import logging
import requests as r
from sys import exit
import time as pytime
from typing import Any


def r_get(url: str, purpose: str, json: dict[str, Any] | None = None, retries: int = 3, delay: int = 2) -> dict[str, Any]:
    """Performs a get request for a given purpose. Ends the program on failure."""
    for attempt in range(1, retries + 1):
        response = r.get(url, json=json)
        if response.ok:
            return response.json()
        logging.warning(f'Attempt {attempt} failed getting {purpose}: {response.status_code}')
        if attempt < retries:
            pytime.sleep(delay)

    logging.critical(f'GET failed fetching {purpose} after {retries} attempts')
    exit(1)


def r_post(url: str, purpose: str, json: dict[str, Any], retries: int = 3, delay: int = 2) -> r.Response:
    """Performs a post request for a given purpose. Ends the program on failure."""
    for attempt in range(1, retries + 1):
        try:
            response = r.post(url, json=json)
            if response.ok:
                logging.info(f'Post request complete for {purpose}')
                return response
            else:
                logging.warning(f'Attempt {attempt} failed posting {purpose}: {response.status_code}')
                if attempt < retries:
                    pytime.sleep(delay)
        except Exception as e:
            logging.error(f'Attempt {attempt} exception posting {purpose}: {e}')
            if attempt < retries:
                pytime.sleep(delay)

    logging.critical(f'Failed post request for {purpose} after {retries} attempts')
    exit(1)
