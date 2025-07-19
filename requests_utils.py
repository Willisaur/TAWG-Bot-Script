import logging
import requests as r
import time as pytime

# Performs a get request for a given purpose
def r_get(url, purpose, json=None, retries=3, delay=2):
    for attempt in range(1, retries + 1):
        response = r.get(url, json=json)
        if response.ok:
            return response.json()
        logging.warning(f'Attempt {attempt} failed getting {purpose}: {response.status_code}')
        if attempt < retries:
            pytime.sleep(delay)
    logging.error(f'Failed getting {purpose} after {retries} attempts')
    return None

# Performs a post request for a given purpose
def r_post(url, purpose, json, retries=3, delay=2):
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
    logging.error(f'Failed post request for {purpose} after {retries} attempts')
    return None
