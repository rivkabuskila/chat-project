import time
import unittest

import pytest as pytest

from client import *

class MyTestCase(unittest.TestCase):

    def test_connect(self):
        ans = connect("rivka")
        self.assertEqual(ans, "<connected>")

    def test_user(self):
        process_request("getusers")
        time.sleep(1)
        ans = message_recv.pop(0)
        self.assertEqual(ans, "<users_lst><1><rivka><end>")

    def test_files(self):
        process_request("getfilelist")
        time.sleep(2)
        ans = message_recv.pop(0)
        print(ans)
        self.assertEqual(ans, "<file_lst><a.txt><b.json><download.png><end>")

    def test_send_message(self):
         process_request("send amit hi")
         time.sleep(3)
         ans = message_recv.pop(0)
         self.assertEqual(ans, "Couldn't find user amit")



if __name__ == '__main__':
    unittest.main()
    process_request("disconnect")

