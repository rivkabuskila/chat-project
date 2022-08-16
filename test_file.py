import time
import unittest
from client import *


class MyTestCase1(unittest.TestCase):
    def test_big_file(self):
        connect("rivka")
        process_request("download" + " " + "final_project.pdf")
        time.sleep(2)
        ans = message_recv.pop(0)
        self.assertEqual(ans, "<File> <final_project.pdf> is too big to send")
        process_request("disconnect")

    def test_File_not_found(self):
        connect("rivka")
        process_request("download" + " " + "final.pdf")
        time.sleep(2)
        ans = message_recv.pop(0)
        self.assertEqual(ans, "<File> <final.pdf> does not exist on the server>")  #
        process_request("disconnect")

if __name__ == '__main__':
    unittest.main()
