# libraries
from datetime import datetime
import json

# project files
from requests_utils import r_get, r_post
from config import (
    ENV_TOKEN,
    ENV_GROUP_ID,
    load_env_vars
)

# environment variables
env = load_env_vars()
TOKEN = env[ENV_TOKEN]
GROUP_ID = env[ENV_GROUP_ID]

URL = f'https://api.groupme.com/v3/groups/{GROUP_ID}?token={TOKEN}'
PURPOSE = 'users' # modify as needed


def main():
    response = r_get(URL, PURPOSE)
    today_str = datetime.now().strftime('%m-%d-%y')
    filename = f'tests/examples/{today_str}_{PURPOSE}.json'

    if response is not None:
        with open(filename, 'w') as file:
            json.dump(response, file, indent=4)
        print(f'Dumped user data to {filename}')
    else:
        print("Failed to get a valid response; no data dumped.")

if __name__ == '__main__':
    main()