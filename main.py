from dotenv import load_dotenv
from os import getenv, path
import requests as r
import json
from datetime import datetime as dt, timedelta, time
from zoneinfo import ZoneInfo
import heapq
import uuid

ENV_TOKEN = 'GROUPME_ACCESS_TOKEN'
ENV_GROUP_ID = 'GROUPME_GROUP_ID'
ENV_SUBGROUP_ID_CHECKINS = 'GROUPME_SUBGROUP_ID_CHECKINS'
ENV_SUBGROUP_ID_STREAKS = 'GROUPME_SUBGROUP_ID_STREAKS'

STREAKS_FILENAME = 'scores.txt'

load_dotenv()
TOKEN = getenv(ENV_TOKEN)
GROUP_ID = getenv(ENV_GROUP_ID)
SUBGROUP_ID_CHECKINS = getenv(ENV_SUBGROUP_ID_CHECKINS)
SUBGROUP_ID_STREAKS = getenv(ENV_SUBGROUP_ID_STREAKS)

URL_USERS = f'https://api.groupme.com/v3/groups/{GROUP_ID}?token={TOKEN}'
URL_CHECKINS = f'https://api.groupme.com/v3/groups/{SUBGROUP_ID_CHECKINS}/messages?token={TOKEN}&acceptFiles=0&limit=20'
URL_MESSAGE = f'https://api.groupme.com/v3/groups/{SUBGROUP_ID_STREAKS}/messages?token={TOKEN}'

_TIMEZONE_EASTERN = ZoneInfo("America/New_York")
_NOW = dt.now(_TIMEZONE_EASTERN)
_YESTERDAY = _NOW.date() - timedelta(days=1)
START_OF_YESTERDAY = dt.combine(_YESTERDAY, time.min, _TIMEZONE_EASTERN)


# Performs a get request for a given purpose
def r_get(url, purpose, json = None):
    response = r.get(url, json=json)

    if not response.ok:
        print(f'Failed getting {purpose}')
        raise response.raise_for_status()
    
    return response.json()

# Parse users from JSON and store them in a map of {user_id: nickname}
def getUsers(data, users_nicknames):
    members = data.get('response', {}).get('members', [])

    for member in members:
        user_id = member.get('user_id')
        name = member.get('nickname')
        users_nicknames[user_id] = name

    print(f'Found {len(users_nicknames)} users: {users_nicknames}')

# Parse checkins from JSON and store 1 (that the user read) in users_streakDiffs accordingly
def getCheckins(data, users_streakDiffs):
    messages = data.get('response', {}).get('messages', [])
    print(f'Found {len(messages)} messsages since {START_OF_YESTERDAY.date()}')
    messages = [msg for msg in messages if 'event' not in msg]
    print(f'Found {len(messages)} non-events since {START_OF_YESTERDAY.date()}')

    i = 0
    while i < len(messages):
        message = messages[i]
        try:
            text = message.get('text')
            checkin_number = int(text[0])
        except:
            raise ValueError(f'Unable to parse number from checkin. message: {message}')
        
        user_id = message.get('user_id')
        users_streakDiffs[user_id] = 1 # mark user has read today

        # print(f'user: {message.get('name')}, checkin: {message.get('text')}')

        # reached first checkin of the day
        if checkin_number == 1:
            print(f'Logged {i+1} checkins from messages')
            break
        else:
            i += 1
    
    if i == len(messages):
        users_streakDiffs.clear()
        print('No one read today')
    
# Read content from a file and return the content as a list of strings
def readFile():
    try:
        with open(STREAKS_FILENAME, 'r') as file:
            return file.readlines()
    except FileNotFoundError:
        return []

# Given streaks from a file (in the format f'{streak} {user_id}\n'), update the streak map
def updateStreaks(fileContent, users_streakDiffs):
    # updates users_streakDiffs to be {user_id: streak, ...}
    for line in fileContent:
        line = line.strip()
        streak, user_id = line.split()
        streak = int(streak)
        diff = users_streakDiffs[user_id]

        # woah this is clean
        if streak ^ diff >= 0: # same sign
            streak += diff # streak increases/decreases in same direction
        else:
            streak = diff # streak switches to -1 or 1
        users_streakDiffs[user_id] = streak

# Given a map of {user_id: streak} and {user_id: nickname}, return the TAWG message body as a list of strings
def getSortedStreaks(users_streakDiffs, users_nicknames):    
    message_body = []
    streak_heap = []
    heapq.heapify(streak_heap)

    for user_id, streak in users_streakDiffs.items():
        heapq.heappush(streak_heap, [-streak, users_nicknames[user_id]])

    while streak_heap:
        streak_negative, nickname = heapq.heappop(streak_heap)
        message_body.append(f'{-streak_negative} {nickname}')
    
    print('Formatted message body')
    return message_body

# Provided a map, write the streaks to files in the format of f'{streak} {user_id}'
def writeStreaksToFile(users_streakDiffs):
    fileContent = []
    for user_id, streak in users_streakDiffs.items():
        fileContent.append(f'{streak} {user_id}')
    
    with open(STREAKS_FILENAME, 'w') as file:
        file.write('\n'.join(fileContent))
    print("Updated streaks file")
        
# Performs a post request for a given purpose
def r_post(url, purpose, json):
    try:
        response = r.post(url, json=json)

        if not response.ok:
            raise response.raise_for_status()
    except:
        print(f'Failed post request for {purpose}')
        raise response.raise_for_status()

    print(f'Post request complete for {purpose}')

# Return post request JSON body for the streak leaderboard
def formatLeaderboard_inJson(data_streaksSorted):
    header = f'TAWG Streaks for {START_OF_YESTERDAY.date()}:'
    messageContent = '\n'.join([header] + data_streaksSorted)
    return {
        'message': {
            'source_guid': str(uuid.uuid1()), # generates a time-based guid
            'text': messageContent
        }}

# json.dump(response.json(), file, indent=4)
# URL = 'https://api.groupme.com/v3/bots/post'
# BODY = {
#     'bot_id': '1172a5cbd84b117ac1bfec90db', 
#     'text': 
# }
# r.post('https://api.groupme.com/v3/bots/post', data=BODY)

def main():
    users_streakDiffs = dict() # user_id: -1 | 1
    users_nicknames = dict() # user_id: nickname

    # get users
    data_users = r_get(URL_USERS, 'users')
    getUsers(data_users, users_nicknames)

    for user_id in users_nicknames.keys():
        users_streakDiffs[user_id] = -1 # by default, people don't read

    # get checkins
    data_checkins = r_get(URL_CHECKINS, 'checkins', {'since_id': dt.timestamp(START_OF_YESTERDAY)}) # gets most recent messages, max 100
    getCheckins(data_checkins, users_streakDiffs)

    # read stored streaks data
    data_streaks = readFile()

    # update streaks with the new checkins
    updateStreaks(data_streaks, users_streakDiffs)
    
    # write the streaks to the file
    writeStreaksToFile(users_streakDiffs)

    # get the streaks as a sorted list
    data_streaksSorted = getSortedStreaks(users_streakDiffs, users_nicknames)

    # Post the streak leaderboard to the groupme chat
    data_leaderboardJson = formatLeaderboard_inJson(data_streaksSorted)
    # r_post(URL_MESSAGE, 'streaks', data_leaderboardJson)

if __name__ == '__main__':
    main()