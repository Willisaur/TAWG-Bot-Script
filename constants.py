# standard library
from datetime import datetime as dt, timedelta, time as dt_time
from dotenv import load_dotenv
import logging
from os import getenv
from urllib.parse import urlencode

# third-party libraries
from zoneinfo import ZoneInfo


# helper functions
def add_query_parameters(token: str, limit: int = 100, accept_files: bool = False) -> str:
    params : dict[str, int | str] = {
        'token': token,
        'after_id': START_OF_YESTERDAY_TIMESTAMP,
        'limit': limit,
        'acceptFiles': int(accept_files)
    }
    return urlencode(params)


def get_env_var(name: str) -> str:
    value = getenv(name)
    if value is None:
        logging.critical(f'Missing required environment variable: {name}')
        exit(1)
    return value


# environment variables
load_dotenv()
ENVIRONMENT = get_env_var("ENVIRONMENT")
GROUPME_ACCESS_TOKEN = get_env_var("GROUPME_ACCESS_TOKEN")
GROUPME_GROUP_ID = get_env_var("GROUPME_GROUP_ID")
GROUPME_SUBGROUP_ID_TAWG1 = get_env_var("GROUPME_SUBGROUP_ID_TAWG1")
GROUPME_SUBGROUP_ID_TAWG2 = get_env_var("GROUPME_SUBGROUP_ID_TAWG2")
GROUPME_SUBGROUP_ID_STREAKS = get_env_var("GROUPME_SUBGROUP_ID_STREAKS")
SUPABASE_ENDPOINT = get_env_var("SUPABASE_ENDPOINT")
SUPABASE_KEY = get_env_var("SUPABASE_KEY")


# constants
_TIMEZONE_EASTERN = ZoneInfo("America/New_York")
_NOW = dt.now(_TIMEZONE_EASTERN)
_NANOSECONDS_MULTIPLIER = 100_000_000

YESTERDAY = _NOW.date() - timedelta(days=2)
START_OF_YESTERDAY_TIMESTAMP = int(dt.timestamp(dt.combine(YESTERDAY, dt_time.min, _TIMEZONE_EASTERN))) * _NANOSECONDS_MULTIPLIER
START_OF_YESTERDAY = dt.fromtimestamp(START_OF_YESTERDAY_TIMESTAMP / _NANOSECONDS_MULTIPLIER).date()

LEADERBOARD_HEADER = f'TAWG Streaks for {START_OF_YESTERDAY}:'

BASE_URL = f'https://api.groupme.com/v3/groups'

URL_USERS = f'{BASE_URL}/{GROUPME_GROUP_ID}?token={GROUPME_ACCESS_TOKEN}'
URL_TAWG1 = f'{BASE_URL}/{GROUPME_SUBGROUP_ID_TAWG1}/messages?{add_query_parameters(GROUPME_ACCESS_TOKEN)}'
URL_TAWG2 = f'{BASE_URL}/{GROUPME_SUBGROUP_ID_TAWG2}/messages?{add_query_parameters(GROUPME_ACCESS_TOKEN)}'
URL_STREAKS = f'{BASE_URL}/{GROUPME_SUBGROUP_ID_STREAKS}/messages?token={GROUPME_ACCESS_TOKEN}'

