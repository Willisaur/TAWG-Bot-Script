# standard library
from datetime import datetime as dt, timedelta, time as dt_time
from dotenv import load_dotenv
import logging
import os
import re
import sqlite3
from sys import exit
import uuid

# third-party libraries
from zoneinfo import ZoneInfo

# load project files
from requests_utils import r_get, r_post


# environment variables
def get_env_var(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        logging.critical(f'Missing required environment variable: {name}')
        exit(1)
    return value

load_dotenv()

GROUPME_ACCESS_TOKEN = get_env_var("GROUPME_ACCESS_TOKEN")
GROUPME_GROUP_ID = get_env_var("GROUPME_GROUP_ID")
GROUPME_SUBGROUP_ID_TAWG1 = get_env_var("GROUPME_SUBGROUP_ID_TAWG1")
GROUPME_SUBGROUP_ID_TAWG2 = get_env_var("GROUPME_SUBGROUP_ID_TAWG2")
GROUPME_SUBGROUP_ID_STREAKS = get_env_var("GROUPME_SUBGROUP_ID_STREAKS")
ENVIRONMENT = get_env_var("ENVIRONMENT")


# constants
URL_USERS = f'https://api.groupme.com/v3/groups/{GROUPME_GROUP_ID}?token={GROUPME_ACCESS_TOKEN}'
URL_TAWG1 = f'https://api.groupme.com/v3/groups/{GROUPME_SUBGROUP_ID_TAWG1}/messages?token={GROUPME_ACCESS_TOKEN}&acceptFiles=0&limit=20' # API limit = 100 msgs, URI limit = 20 msgs
URL_TAWG2 = f'https://api.groupme.com/v3/groups/{GROUPME_SUBGROUP_ID_TAWG2}/messages?token={GROUPME_ACCESS_TOKEN}&acceptFiles=0&limit=20' # API limit = 100 msgs, URI limit = 20 msgs
URL_MESSAGE = f'https://api.groupme.com/v3/groups/{GROUPME_SUBGROUP_ID_STREAKS}/messages?token={GROUPME_ACCESS_TOKEN}'


_TIMEZONE_EASTERN = ZoneInfo("America/New_York")
_NOW = dt.now(_TIMEZONE_EASTERN)
_YESTERDAY = _NOW.date() - timedelta(days=1)
START_OF_YESTERDAY = dt.combine(_YESTERDAY, dt_time.min, _TIMEZONE_EASTERN)
LEADERBOARD_HEADER = f'TAWG Streaks for {START_OF_YESTERDAY.date()}:'

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


def database_connect() -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    """Connect to the sqlite database and create the streaks table if not found"""
    try:
        conn = sqlite3.connect('streaks.db')
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
    data = r_get(URL_USERS, 'users')

    users_nicknames = dict()
    users_streak_diffs = dict()
    members = data.get('response', {}).get('members', [])

    for member in members:
        user_id = member.get('user_id')
        name = member.get('nickname')

        if not (user_id and name):
            logging.warning(f'Missing user_id or nickname when parsing users GET request')
            continue

        users_nicknames[user_id] = name
        users_streak_diffs[user_id] = -1 # by default, people don't read

    if not len(users_nicknames):
        logging.critical('GET resulted in no users')
        exit(1)
    
    logging.info(f'Found {len(users_nicknames)} users: {users_nicknames}')
    return users_nicknames, users_streak_diffs


def get_checkins(url: str, chat_name: str, users_streak_diffs: dict[str, int]) -> None:
    """Parse checkins from JSON and store `1` (that the user read) in `users_streak_diffs` accordingly"""
    data = r_get(url, f'{chat_name} checkins', {'since_id': dt.timestamp(START_OF_YESTERDAY)})

    messages_unfiltered = data.get('response', {}).get('messages', [])
    messages = [msg for msg in messages_unfiltered if 'event' not in msg]
    logging.info(f'Found {len(messages_unfiltered)} messages in chat_name: {chat_name} since {START_OF_YESTERDAY.date()}')
    logging.info(f'Found {len(messages)} non-events in chat_name: {chat_name} since {START_OF_YESTERDAY.date()}')

    last_checkin_number = len(messages)
    checkin_count = 0

    for i in range(len(messages)):
        message = messages[i]
        try:
            text = message.get('text')
            match = re.match(r'^(\d+)\??\)', text) # a number followed by a possible ? and mandatory )
            if match:
                checkin_number = int(match.group(1))
            else:
                logging.warning(f'Most recent message i: {i} from chat_name:{chat_name} not prefixed with "#)"')
                continue
        except Exception:
            logging.error(f'Unable to parse text from message: {message}')
            continue

        if checkin_number > last_checkin_number: # checkin prefix not descending
            logging.warning(f'Stopped parsing at out-of-order checkin message i: {i}')
            break

        user_id = message.get('user_id')
        users_streak_diffs[user_id] = 1 # mark user has read today
        checkin_count += 1

        if checkin_number == 1: # reached first checkin of the day
            logging.info(f'Logged {checkin_count} checkins from messages')
            break

    if checkin_count == 0:
        logging.info('No one read today')


def read_db(cursor: sqlite3.Cursor) -> list[tuple[str, int]]:
    """Read the streaks from the sqlite database -- returns `[(user_id, streak)]`"""
    try:
        cursor.execute('SELECT * FROM streaks')
        rows = cursor.fetchall()
        logging.info(f"Successfully fetched {len(rows)} rows from streaks table")
        return rows
    except Exception as e:
        logging.critical(f"Failed to fetch from database: {e}")
        exit(1)


def update_streaks_map(cursor: sqlite3.Cursor, users_streak_diffs: dict[str, int]) -> None:
    """Query the database, and update the streak map"""
    data = read_db(cursor)
    
    for row in data:
        user_id, streak = row
        diff = users_streak_diffs[user_id]

        # increment, decrement, or reset based on signs
        if streak ^ diff >= 0: # same sign
            streak += diff # streak increases/decreases in same direction
        else:
            streak = diff # streak switches to -1 or 1
        users_streak_diffs[user_id] = streak # updates users_streak_diffs to be {user_id: streak, ...}


def get_sorted_streaks(users_nicknames: dict[str, str], users_streak_diffs: dict[str, int]) -> list[str]:
    """Given a map of `{user_id: streak}` and `{user_id: nickname}`, return a list of strings in the format of `{streak} {nickname}`, sorted by streak descending.
    """
    message_body = [
        f"{streak} {users_nicknames[user_id]}"
        for user_id, streak in sorted(users_streak_diffs.items(), key=lambda x: x[1], reverse=True)
    ]
    logging.info('Sorted streaks')
    return message_body


def write_streaks_to_db(conn: sqlite3.Connection, cursor: sqlite3.Cursor, users_streak_diffs: dict):
    """Write the streaks to a database with columns `user_id` and `streak`"""
    update_streaks_map(cursor, users_streak_diffs)

    try:
        for user_id, streak in users_streak_diffs.items():
            cursor.execute('''
                INSERT INTO streaks (user_id, streak) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET streak=excluded.streak
            ''', (user_id, streak))
        conn.commit()
        logging.info(f"Successfully wrote {len(users_streak_diffs)} streaks to the database")
    except Exception as e:
        logging.critical(f"Failed to write streaks to the database: {e}")
        exit(1)


def post_leaderboard(users_nicknames: dict[str, str], users_streak_diffs: dict[str, int]) -> None:
    """Send the streak leaderboard in the groupme chat"""
    sorted_streaks = get_sorted_streaks(users_nicknames, users_streak_diffs)

    message = '\n'.join([LEADERBOARD_HEADER] + sorted_streaks)
    logging.info(f'Generated leaderboard')
    logging.debug(f'Leaderboard: {message}')

    data = {
        'message': {
            'source_guid': str(uuid.uuid1()), # generates a time-based guid
            'text': message
        }}
    
    if ENVIRONMENT == 'prod':
        r_post(URL_MESSAGE, 'streaks leaderboard', data)
    logging.info('Program succeeded')


def main():
    conn, cursor = database_connect()

    users_nicknames, users_streak_diffs = get_users()

    get_checkins(URL_TAWG1, 'TAWG 1', users_streak_diffs)
    get_checkins(URL_TAWG2, 'TAWG 2', users_streak_diffs)

    write_streaks_to_db(conn, cursor, users_streak_diffs)

    post_leaderboard(users_nicknames, users_streak_diffs)

    conn.close()


if __name__ == '__main__':
    main()
