# standard library
import logging
import requests as r
from sys import exit
import time as pytime
from typing import Any

# project files
from constants import (
    URL_USERS,
    URL_TAWG1,
    URL_TAWG2,
    URL_STREAKS
)


# helper functions
def get_purpose(url):
    params = {
        URL_USERS: 'get_users',
        URL_TAWG1: 'get_tawg1',
        URL_TAWG2: 'get_tawg2',
        URL_STREAKS: 'post_leaderboard'
    }
    return params[url]


def r_get(url: str, retries: int = 3, delay: int = 2) -> dict[str, Any]:
    """Performs a get request with retries. Ends the program on failure."""
    for attempt in range(1, retries + 1):
        response = r.get(url)
        if response.ok:
            return response.json()
        logging.warning(f'Attempt {attempt} failed getting {get_purpose(url)}: {response.status_code}')
        if attempt < retries:
            pytime.sleep(delay)

    logging.critical(f'GET failed fetching {get_purpose(url)} after {retries} attempts')
    exit(1)


def r_post(url: str,json: dict[str, Any], retries: int = 3, delay: int = 2) -> r.Response:
    """Performs a post request with retries. Ends the program on failure."""
    for attempt in range(1, retries + 1):
        try:
            response = r.post(url, json=json)
            if response.ok:
                logging.info(f'Post request complete for {get_purpose(url)}')
                return response
            else:
                logging.warning(f'Attempt {attempt} failed posting {get_purpose(url)}: {response.status_code}')
                if attempt < retries:
                    pytime.sleep(delay)
        except Exception as e:
            logging.error(f'Attempt {attempt} exception posting {get_purpose(url)}: {e}')
            if attempt < retries:
                pytime.sleep(delay)

    logging.critical(f'Failed post request for {get_purpose(url)} after {retries} attempts')
    exit(1)

