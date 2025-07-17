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

users_streakDiffs = dict() # user_id: -1 | 1
users_nicknames = dict() # user_id: nickname

# Get users
def getUsers():
    response = r.get(URL_USERS)

    if not response.ok:
        print('Failed getting users')
        raise response.raise_for_status()
    
    data = response.json()
    members = data.get('response', {}).get('members', [])

    for member in members:
        name = member.get('nickname')
        user_id = member.get('user_id')

        users_streakDiffs[user_id] = -1
        users_nicknames[user_id] = name

    print(f'Found {len(users_nicknames)} users: {users_nicknames}')
    

# Get checkins
def getCheckins():
    response = r.get(URL_CHECKINS, data = {
        'since_id': dt.timestamp(START_OF_YESTERDAY) # gets most recent messages, max 100
    })

    if not response.ok:
        print('Failed getting checkins')
        raise response.raise_for_status()
    
    data = response.json()
    messages = data.get('response', {}).get('messages', [])
    print(f'Found {len(messages)} messsages since {START_OF_YESTERDAY.date()}')
    messages = [msg for msg in messages if 'event' not in msg]
    print(f'Found {len(messages)} non-events since {START_OF_YESTERDAY.date()}')

    for i in range(len(messages)):
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
    

def updateStreaks():
    # create the file if it doesn't exist
    if not path.exists(STREAKS_FILENAME):
        with open(STREAKS_FILENAME, 'w') as file:
            pass

    with open(STREAKS_FILENAME, 'r+') as file:
        lines = file.readlines()
        # print(lines)
        file.seek(0)
        users_to_ignore = set()

        # update streak
        for line in lines:
            line = line.strip()
            user_id, streak = line.split()
            streak = int(streak)
            diff = users_streakDiffs[user_id]

            # woah this is clean
            if streak ^ diff >= 0: # same sign
                streak += diff # streak increases/decreases in same direction
            else:
                streak = diff # streak switches to -1 or 1
            
            file.write(f'{streak} {user_id}\n')
            users_to_ignore.add(user_id)

        for user_id, streak in users_streakDiffs.items():
            if user_id not in users_to_ignore:
                file.write(f'{streak} {user_id}\n')

        print("Updated streaks file")
        
def printStreaks():
    # read and sort streaks
    message = [f'TAWG Streaks for {START_OF_YESTERDAY.date()}:']
    streak_heap = []
    heapq.heapify(streak_heap)

    try:
        with open(STREAKS_FILENAME, 'r') as file:
            for line in file.readlines():
                streak, user_id = line.strip().split()
                streak = int(streak)

                heapq.heappush(streak_heap, [-streak, users_nicknames[user_id]]) # min heap
    except:
        print('Could not open streak file after updating streaks')
        raise(open)
    
    while streak_heap:
        streak, nickname = heapq.heappop(streak_heap)
        message.append(f'{-streak} - {nickname}') # min heap
    print('Prepared message to post')

    # send message in chat
    r.post(URL_MESSAGE, json={
        'message': {
            'source_guid': str(uuid.uuid1()), # generates a time-based guid
            'text': '\n'.join(message)
        }
    })

# json.dump(response.json(), file, indent=4)
# URL = 'https://api.groupme.com/v3/bots/post'
# BODY = {
#     'bot_id': '1172a5cbd84b117ac1bfec90db', 
#     'text': 
# }
# r.post('https://api.groupme.com/v3/bots/post', data=BODY)

def main():
    getUsers()
    getCheckins()
    updateStreaks()
    printStreaks()

if __name__ == '__main__':
    main()