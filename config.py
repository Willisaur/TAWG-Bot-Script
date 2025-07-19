import os
from dotenv import load_dotenv
from typing import Dict

ENV_TOKEN = 'GROUPME_ACCESS_TOKEN'
ENV_GROUP_ID = 'GROUPME_GROUP_ID'
ENV_SUBGROUP_ID_CHECKINS = 'GROUPME_SUBGROUP_ID_CHECKINS'
ENV_SUBGROUP_ID_STREAKS = 'GROUPME_SUBGROUP_ID_STREAKS'
ENV_STREAKS_FILENAME = 'STREAKS_FILENAME'

def load_env_vars() -> Dict[str, str]:
    """Load and validate required environment variables."""
    load_dotenv()
    keys = [
        ENV_TOKEN,
        ENV_GROUP_ID,
        ENV_SUBGROUP_ID_CHECKINS,
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
