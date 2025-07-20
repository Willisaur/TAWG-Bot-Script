# standard library
from datetime import datetime as dt, timedelta, time as dt_time
from dotenv import load_dotenv
import heapq
import logging
import os
import re
import uuid

# third-party libraries
from zoneinfo import ZoneInfo

# load project files
from requests_utils import r_get, r_post


# environment variables
ENV_TOKEN = 'GROUPME_ACCESS_TOKEN'
ENV_GROUP_ID = 'GROUPME_GROUP_ID'
ENV_SUBGROUP_ID_CHECKINS_TAWG1 = 'GROUPME_SUBGROUP_ID_CHECKINS_TAWG1'
ENV_SUBGROUP_ID_CHECKINS_TAWG2 = 'GROUPME_SUBGROUP_ID_CHECKINS_TAWG2'
ENV_SUBGROUP_ID_STREAKS = 'GROUPME_SUBGROUP_ID_STREAKS'
ENV_STREAKS_FILENAME = 'STREAKS_FILENAME'

def load_env_vars():
    """Load and validate required environment variables."""
    load_dotenv()
    keys = [
        ENV_TOKEN,
        ENV_GROUP_ID,
        ENV_SUBGROUP_ID_CHECKINS_TAWG1,
        ENV_SUBGROUP_ID_CHECKINS_TAWG2,
        ENV_SUBGROUP_ID_STREAKS,
        ENV_STREAKS_FILENAME
    ]
    env = {}
    missing = []
    for key in keys:
        value = os.getenv(key)
        if value is None:
            missing.append(key)
        env[key] = value
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
    return env

env = load_env_vars()
TOKEN = env[ENV_TOKEN]
GROUP_ID = env[ENV_GROUP_ID]
SUBGROUP_ID_CHECKINS_TAWG1 = env[ENV_SUBGROUP_ID_CHECKINS_TAWG1]
SUBGROUP_ID_CHECKINS_TAWG2 = env[ENV_SUBGROUP_ID_CHECKINS_TAWG2]
SUBGROUP_ID_STREAKS = env[ENV_SUBGROUP_ID_STREAKS]
STREAKS_FILENAME = env[ENV_STREAKS_FILENAME]


# constants
URL_USERS = f'https://api.groupme.com/v3/groups/{GROUP_ID}?token={TOKEN}'
URL_CHECKINS_TAWG1 = f'https://api.groupme.com/v3/groups/{SUBGROUP_ID_CHECKINS_TAWG1}/messages?token={TOKEN}&acceptFiles=0&limit=20' # hard limit == 100
URL_CHECKINS_TAWG2 = f'https://api.groupme.com/v3/groups/{SUBGROUP_ID_CHECKINS_TAWG2}/messages?token={TOKEN}&acceptFiles=0&limit=20' # hard limit == 100
URL_MESSAGE = f'https://api.groupme.com/v3/groups/{SUBGROUP_ID_STREAKS}/messages?token={TOKEN}'

_TIMEZONE_EASTERN = ZoneInfo("America/New_York")
_NOW = dt.now(_TIMEZONE_EASTERN)
_YESTERDAY = _NOW.date() - timedelta(days=1)
START_OF_YESTERDAY = dt.combine(_YESTERDAY, dt_time.min, _TIMEZONE_EASTERN)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


def get_users(data, users_nicknames):
    """Parse users from JSON and store them in a map of {user_id: nickname}"""
    members = data.get('response', {}).get('members', [])

    for member in members:
        user_id = member.get('user_id')
        name = member.get('nickname')
        users_nicknames[user_id] = name

    logging.info(f'Found {len(users_nicknames)} users: {users_nicknames}')


def get_checkins(data, users_streakDiffs):
    """Parse checkins from JSON and store 1 (that the user read) in users_streakDiffs accordingly """
    messages = data.get('response', {}).get('messages', [])
    logging.info(f'Found {len(messages)} messages since {START_OF_YESTERDAY.date()}')
    messages = [msg for msg in messages if 'event' not in msg]
    logging.info(f'Found {len(messages)} non-events since {START_OF_YESTERDAY.date()}')

    lastCheckinNumber = len(messages)
    checkinCount = 0
    for i in range(len(messages)):
        message = messages[i]
        try:
            text = message.get('text')
            match = re.match(r'^(\d+)\??\)', text) # a number followed by )
            if match:
                checkin_number = int(match.group(1))
            else:
                logging.warning(f'Message {i} not prefixed with "#)"')
                continue
        except Exception:
            raise ValueError(f'Unable to parse number from checkin. message: {message}')

        # checkin prefix not descending
        if checkin_number > lastCheckinNumber:
            logging.warning(f'Stopped parsing at out-of-order checkin message i: {i}')
            break

        user_id = message.get('user_id')
        users_streakDiffs[user_id] = 1 # mark user has read today
        checkinCount += 1
        # logging.debug(f'user: {message.get('name')}, checkin: {message.get('text')}')

        # reached first checkin of the day
        if checkin_number == 1:
            logging.info(f'Logged {checkinCount} checkins from messages')
            break

    if checkinCount == 0:
        users_streakDiffs.clear()
        logging.info('No one read today')

def read_file():
    """Read content from a file and return the content as a list of strings"""
    try:
        with open(STREAKS_FILENAME, 'r') as file:
            return file.readlines()
    except FileNotFoundError:
        return []


def update_streaks(file_content, users_streak_diffs):
    """Given streaks from a file (in the format f'{streak} {user_id}\n'), update the streak map"""
    for line in file_content:
        line = line.strip()
        streak, user_id = line.split()
        streak = int(streak)
        diff = users_streak_diffs[user_id]

        # woah this is clean
        if streak ^ diff >= 0: # same sign
            streak += diff # streak increases/decreases in same direction
        else:
            streak = diff # streak switches to -1 or 1
        users_streak_diffs[user_id] = streak # updates users_streak_diffs to be {user_id: streak, ...}


def get_sorted_streaks(users_streak_diffs, users_nicknames):
    """Given a map of {user_id: streak} and {user_id: nickname}, return the TAWG message body as a list of strings"""
    message_body = []
    streak_heap = []
    heapq.heapify(streak_heap)

    for user_id, streak in users_streak_diffs.items():
        heapq.heappush(streak_heap, [-streak, users_nicknames[user_id]])

    while streak_heap:
        streak_negative, nickname = heapq.heappop(streak_heap)
        message_body.append(f'{-streak_negative} {nickname}')

    logging.info('Formatted message body')
    return message_body


def write_streaks_to_file(users_streak_diffs):
    """Provided a map, write the streaks to files in the format of f'{streak} {user_id}'"""
    fileContent = []
    for user_id, streak in users_streak_diffs.items():
        fileContent.append(f'{streak} {user_id}')

    with open(STREAKS_FILENAME, 'w') as file:
        file.write('\n'.join(fileContent))
    logging.info("Updated streaks file")


def format_leaderboard_in_json(data_streaks_sorted):
    """Return post request JSON body for the streak leaderboard"""
    header = f'TAWG Streaks for {START_OF_YESTERDAY.date()}:'
    messageContent = '\n'.join([header] + data_streaks_sorted)
    return {
        'message': {
            'source_guid': str(uuid.uuid1()), # generates a time-based guid
            'text': messageContent
        }}


def main():
    users_streak_diffs = dict() # {user_id: -1 or 1}
    users_nicknames = dict() # {user_id: nickname}

    # get users
    data_users = r_get(URL_USERS, 'users')
    get_users(data_users, users_nicknames)

    for user_id in users_nicknames.keys():
        users_streak_diffs[user_id] = -1 # by default, people don't read

    # get checkins from both chats
    data_checkins_tawg1 = r_get(URL_CHECKINS_TAWG1, 'checkins', {'since_id': dt.timestamp(START_OF_YESTERDAY)}) # gets most recent messages, hard max 100, soft limit 20
    data_checkins_tawg2 = r_get(URL_CHECKINS_TAWG2, 'checkins', {'since_id': dt.timestamp(START_OF_YESTERDAY)}) # gets most recent messages, hard max 100, soft limit 20
    get_checkins(data_checkins_tawg1, users_streak_diffs)
    get_checkins(data_checkins_tawg2, users_streak_diffs)

    # read stored streaks data
    data_streaks = read_file()

    # update streaks with the new checkins
    update_streaks(data_streaks, users_streak_diffs)

    # write the streaks to the file
    write_streaks_to_file(users_streak_diffs)

    # get the streaks as a sorted list
    data_streaks_sorted = get_sorted_streaks(users_streak_diffs, users_nicknames)

    # Post the streak leaderboard to the groupme chat
    data_leaderboard_json = format_leaderboard_in_json(data_streaks_sorted)
    r_post(URL_MESSAGE, 'streaks', data_leaderboard_json)


if __name__ == '__main__':
    main()