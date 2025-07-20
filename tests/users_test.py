# import files
import main

# import libraries
import unittest
from unittest.mock import patch
import json

class Test_Users(unittest.TestCase):
    @patch('requests_utils.r_get')
    def test_get_users(self, mock_r_get):
        # Load sample response from a file
        with open('tests/examples/07-19-25_users.json') as sample:
            mock_r_get.return_value = json.load(sample)
        users_nicknames_sample, users_streak_diffs_sample = main.get_users()
        
        with open('tests/examples/07-19-25_users_parsed.json') as actual:
            users_nicknames_actual = json.load(actual)
        self.assertEqual(users_nicknames_actual, users_nicknames_sample)


if __name__ == '__main__':
    unittest.main()
