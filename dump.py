# libraries
from datetime import datetime as dt
import json

# project files
from requests_helpers import (
    get_purpose,
    r_get,
    r_post
)
from constants import (
    YESTERDAY,
    URL_USERS,
    URL_TAWG1,
    URL_TAWG2
)


# constants
URL = URL_TAWG1


def main():
    response = r_get(URL)
    today_str = dt.now().strftime('%m-%d-%y')
    filename = f'tests/examples/{YESTERDAY}_{get_purpose(URL)}.json'

    if response is not None:
        with open(filename, 'w') as file:
            json.dump(response, file, indent=4)
        print(f'Dumped user data to {filename}')
    else:
        print("Failed to get a valid response; no data dumped.")

if __name__ == '__main__':
    main()