# import files
import main

# import libraries
import unittest
import json

class Test_Users(unittest.TestCase):
    def test_GetUsersCount_Successful(self):
        # arrange
        with open('tests/examples/07-19-25_users.json') as file:
            data = json.load(file)

        # act
        users_nicknames = {}
        main.get_users(data, users_nicknames)

        # assert
        self.assertEqual(data['response']['members_count'], len(users_nicknames))


if __name__ == '__main__':
    unittest.main()
