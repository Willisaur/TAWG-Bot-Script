# TAWG Bot Script

**TAWG** stands for "Time alone with God." TAWG takes many forms, including Bible reading. This script powers an automated GroupMe bot designed to track and announce daily Bible reading streaks for a group. It collects check-in messages from designated GroupMe chats, calculates each user's reading streak, and posts a leaderboard to a GroupMe groupchat channel.

## Features

- **Daily Streak Tracking:** Monitors check-in messages to determine which users have read each day.
- **Leaderboard Posting:** Automatically posts a formatted leaderboard of current streaks to a GroupMe group.
- **Persistent Streak Storage:** Accesses a local SQLite database for persistence across runs.

## How It Works

1. **User Check-ins:** Users post numbered check-in messages (e.g., `1)`, `2)`) in designated GroupMe chats.
2. **Data Collection:** The script fetches recent messages from these chats and parses check-ins.
3. **Streak Calculation:** Streaks are updated based on whether users checked in for the day.
4. **Leaderboard Generation:** A sorted leaderboard is created and posted to a GroupMe group.
5. **Persistence:** Streaks are saved to an SQLite database for future runs.

## File Structure

- `main.py` - Main logic for fetching check-ins, updating streaks, and posting the leaderboard.
- `requests_utils.py` - Utility functions for making HTTP requests.
- `dump.py` - Utility for dumping user data from GroupMe for testing.
- `tests/` - Unit tests and example data.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE)
