import unittest
from requests import get

PATHKEY = ['insert','your','key','here']
BASEURL = 'https://something.something.net' # the base URL for this function

def makeReq(strPath):
    return get(BASEURL+strPath).json()

class TestPathLock(unittest.TestCase):

    def test_for_dummy(self):
        print("[*] Asking for a random path...")
        # Note: assumes DEBUG is on
        resp = makeReq('/someRandomPath')
        print("Obtained the following:")
        print(resp)
        self.assertEqual(resp['path'], '/someRandomPath', "Should be the same path in a dummy request")


    def test_for_straight_win(self):
        print("[*] Sending the win condition...")
        for key in PATHKEY:
            resp = makeReq('/' + key)
        print("Obtained the following:")
        print(resp)
        self.assertEqual(resp['win'], 'True', "We should win with the key!")

if __name__ == '__main__':
    unittest.main()