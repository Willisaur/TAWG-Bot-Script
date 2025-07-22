# standard library
import logging
import re
from sqlite3 import connect, Connection, Cursor
from sys import exit
import uuid

# third-party libraries
from supabase import create_client, Client

# project files
from requests_helpers import r_get, r_post
from constants import (
    ENVIRONMENT,
    START_OF_YESTERDAY,
    LEADERBOARD_HEADER,
    URL_USERS,
    URL_TAWG1,
    URL_TAWG2,
    URL_STREAKS,
    SUPABASE_ENDPOINT,
    SUPABASE_KEY
)


# config
logging.basicConfig(level=logging.DEBUG if ENVIRONMENT == 'prod' else logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')


# helper methods
def database_connect() -> tuple[Connection, Cursor]:
    """Connect to the sqlite database and create the streaks table if not found"""
    try:
        # Client = create_client(SUPABASE_ENDPOINT, SUPABASE_KEY)

        conn = connect('streaks.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS streaks (
                user_id TEXT PRIMARY KEY,
                streak INTEGER
            )
        ''')
        return conn, cursor
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
    logging.info(f'Found {len(messages_unfiltered)} messages in {chat_name} since {START_OF_YESTERDAY}')
    logging.info(f'Found {len(messages)} non-events in {chat_name} since {START_OF_YESTERDAY}')

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
                logging.warning(f'Message i: {i} from {chat_name} not prefixed with "#)"')
                continue
        except Exception:
            logging.error(f'Unable to parse text from message: {message}')
            continue

        if checkin_number > last_checkin_number + 1:
            logging.warning(f'Checkin number > expected. Ignoring checkin')
            continue
        elif checkin_number < last_checkin_number + 1:
            logging.warning(f'Checkin number < previous. Stopping further parsing.')
            break
        

        user_id = message.get('user_id')
        users_streak_variations[user_id] = 1 # mark user has read today
        last_checkin_number += 1

    if last_checkin_number == 0:
        logging.info('No one read today')
    else:
        logging.info(f'Logged {last_checkin_number} checkins from messages')


def read_db(cursor: Cursor) -> list[tuple[str, int]]:
    """Read the streaks from the sqlite database -- returns `[(user_id, streak)]`"""
    try:
        cursor.execute('SELECT * FROM streaks')
        rows = cursor.fetchall()
        logging.info(f"Successfully fetched {len(rows)} rows from streaks table")
        return rows
    except Exception as e:
        logging.critical(f"Failed to fetch from database: {e}")
        exit(1)


def update_streaks_map(cursor: Cursor, users_streak_variations: dict[str, int]) -> None:
    """Query the database, and update the streak map"""
    data = read_db(cursor)
    
    for row in data:
        user_id, streak = row
        diff = users_streak_variations[user_id]

        # increment, decrement, or reset based on signs
        if streak ^ diff >= 0: # same sign
            streak += diff # streak increases/decreases in same direction
        else:
            streak = diff # streak switches to -1 or 1
        users_streak_variations[user_id] = streak # updates users_streak_variations to be {user_id: streak, ...}


def get_sorted_streaks(users_nicknames: dict[str, str], users_streak_variations: dict[str, int]) -> list[str]:
    """Given a map of `{user_id: streak}` and `{user_id: nickname}`, return a list of strings in the format of `{streak} {nickname}`, sorted by streak descending.
    """
    message_body = [
        f"{streak} {users_nicknames[user_id]}"
        for user_id, streak in sorted(users_streak_variations.items(), key=lambda x: x[1], reverse=True)
    ]
    logging.info('Sorted streaks')
    return message_body


def write_streaks_to_db(conn: Connection, cursor: Cursor, users_streak_variations: dict):
    """Write the streaks to a database with columns `user_id` and `streak`"""
    update_streaks_map(cursor, users_streak_variations)

    try:
        for user_id, streak in users_streak_variations.items():
            cursor.execute('''
                INSERT INTO streaks (user_id, streak) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET streak=excluded.streak
            ''', (user_id, streak))
        conn.commit()
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
    conn, cursor = database_connect()

    users_nicknames, users_streak_variations = get_users()

    get_checkins(URL_TAWG1, 'TAWG 1', users_streak_variations)
    get_checkins(URL_TAWG2, 'TAWG 2', users_streak_variations)

    write_streaks_to_db(conn, cursor, users_streak_variations)

    post_leaderboard(users_nicknames, users_streak_variations)

    conn.close()


if __name__ == '__main__':
    main()
