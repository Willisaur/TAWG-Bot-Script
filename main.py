# standard library
import logging
import re
from sys import exit
from typing import Any
import uuid

# third-party libraries
from supabase import create_client, Client

# project files
from requests_helpers import r_get, r_post
from constants import (
    ENVIRONMENT,
    YESTERDAY,
    LEADERBOARD_HEADER,
    URL_USERS,
    URL_TAWG1,
    URL_TAWG2,
    URL_STREAKS,
    SUPABASE_ENDPOINT,
    SUPABASE_KEY
)


# config
def set_logging_debug():
    if ENVIRONMENT != 'prod':
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
    else:
        set_logging_info()


def set_logging_info():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


set_logging_debug()


# helper methods
def database_connect() -> Client:
    """Connect to the Supabase Postgres database"""
    try:
        set_logging_info()
        Client = create_client(SUPABASE_ENDPOINT, SUPABASE_KEY)
        set_logging_debug()

        return Client
    except Exception as e:
        logging.critical(f"Failed to connect to the database: {e}")
        exit(1)


def get_users() -> tuple[dict[str, str], dict[str, int]]:
    """Parse users from response JSON and store them in a map of `{user_id: nickname}`. Also, create a default dict where each user hasn't read by default"""
    data = r_get(URL_USERS)

    users_nicknames = dict()
    users_streak_variations = dict()
    members = data.get('response', {}).get('members', [])

    for member in members:
        user_id = member.get('user_id')
        name = member.get('nickname')

        if not (user_id and name):
            logging.warning(f'Missing user_id or nickname when parsing users GET request')
            continue

        users_nicknames[user_id] = name
        users_streak_variations[user_id] = -1 # by default, people don't read

    if not len(users_nicknames):
        logging.critical('GET resulted in no users')
        exit(1)
    
    logging.info(f'Found {len(users_nicknames)} users: {users_nicknames}')
    return users_nicknames, users_streak_variations


def get_checkins(url: str, chat_name: str, users_streak_variations: dict[str, int]) -> None:
    """Parse checkins from JSON and store `1` (that the user read) in `users_streak_variations` accordingly"""
    data = r_get(url)

    messages_unfiltered = data.get('response', {}).get('messages', [])
    messages = [msg for msg in messages_unfiltered if 'event' not in msg]
    logging.info(f'Found {len(messages_unfiltered)} messages in {chat_name} since {YESTERDAY}')
    logging.info(f'Found {len(messages)} non-events in {chat_name} since {YESTERDAY}')

    last_checkin_number = 0

    for i in range(len(messages)):
        message = messages[i]
        try:
            text = message.get('text')
            match = re.match(r'^(\d+)\??[)\.]', text)  # a number followed by a possible ? and mandatory ) or .
            if match:
                checkin_number = int(match.group(1))
                logging.debug(f'Checkin found. i: {i}, text: {text}')
            else:
                logging.warning(f'Skipping message i: {i} from {chat_name} not prefixed with "#)"')
                continue
        except Exception:
            logging.error(f'Unable to parse text from message: {message}')
            continue

        if checkin_number != last_checkin_number + 1:
            if checkin_number > last_checkin_number:
                logging.warning(f'Checkin number > expected. Ignoring checkin')
                continue
            else:
                logging.warning(f'Checkin number <= previous. Stopping further parsing.')
                break
        

        user_id = message.get('user_id')
        users_streak_variations[user_id] = 1 # mark user has read today
        last_checkin_number += 1

    if last_checkin_number == 0:
        logging.info('No one read today')
    else:
        logging.info(f'Logged {last_checkin_number} checkins from messages')


def read_database(supabase: Client) -> list[dict[str, Any]]:
    """Read the streaks from the supabase postgres database -- returns `[(user_id, streak)]`"""
    try:
        set_logging_info()
        response = supabase.table('streaks').select('user_id, streak').execute()
        set_logging_debug()
        
        logging.info(f"Successfully fetched {len(response.data)} rows from streaks table")
        return response.data
    except Exception as e:
        logging.critical(f"Failed to fetch from database: {e}")
        exit(1)


def update_streaks_map(supabase: Client, users_streak_variations: dict[str, int]) -> None:
    """Query the database, and update the streak map"""
    data = read_database(supabase)
    
    for row in data:
        user_id = row['user_id']
        streak = row['streak']
        diff = users_streak_variations[user_id]

        # increment, decrement, or reset based on signs
        if streak ^ diff >= 0: # same sign
            streak += diff # streak increases/decreases in same direction
        else:
            streak = diff # streak switches to -1 or 1
        users_streak_variations[user_id] = streak # updates users_streak_variations to be {user_id: streak, ...}


def get_sorted_streaks(users_nicknames: dict[str, str], users_streak_variations: dict[str, int]) -> list[str]:
    """Given a map of `{user_id: streak}` and `{user_id: nickname}`, return a list of strings in the format of `{streak} {nickname}`, sorted by streak descending, then nickname ascending."""
    message_body = [
        f"{streak} - {users_nicknames[user_id]}"
        for user_id, streak in sorted(
            users_streak_variations.items(),
            key=lambda x: (-x[1], users_nicknames[x[0]].lower())
        )
    ]
    logging.info('Sorted streaks')
    return message_body


def write_streaks_to_database(supabase: Client, users_streak_variations: dict[str, int]):
    """Write the streaks to a database with columns `user_id` and `streak`"""
    update_streaks_map(supabase, users_streak_variations)

    if ENVIRONMENT == 'prod':
        try:
            set_logging_info()
            for user_id, streak in users_streak_variations.items():
                supabase.table('streaks').upsert({
                    'user_id': user_id,
                    'streak': streak
                }).execute()
            set_logging_debug()

            logging.info(f"Successfully wrote {len(users_streak_variations)} streaks to the database")
        except Exception as e:
            logging.critical(f"Failed to write streaks to the database: {e}")
            exit(1)


def post_leaderboard(users_nicknames: dict[str, str], users_streak_variations: dict[str, int]) -> None:
    """Send the streak leaderboard in the groupme chat"""
    sorted_streaks = get_sorted_streaks(users_nicknames, users_streak_variations)

    message = '\n'.join([LEADERBOARD_HEADER] + sorted_streaks)
    logging.info(f'Generated leaderboard')
    logging.debug(f'Leaderboard: {message}')

    data = {
        'message': {
            'source_guid': str(uuid.uuid1()), # generates a time-based guid
            'text': message
        }}
    
    if ENVIRONMENT == 'prod':
        r_post(URL_STREAKS, data)
    logging.info('Program succeeded')


def main():
    users_nicknames, users_streak_variations = get_users()

    get_checkins(URL_TAWG1, 'TAWG 1', users_streak_variations)
    get_checkins(URL_TAWG2, 'TAWG 2', users_streak_variations)

    supabase = database_connect()
    write_streaks_to_database(supabase, users_streak_variations)

    post_leaderboard(users_nicknames, users_streak_variations)


if __name__ == '__main__':
    main()
