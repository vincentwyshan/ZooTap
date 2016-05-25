#coding=utf8

import unittest

from tap.service.rpcstats import get_client

class TestSimpleRequest(unittest.TestCase):
    def setUp(self):
        self.client = get_client()

    def tearDown(self):
        pass

    def test_10000_request(self):
        for i in range(1000000):
            # self.client = get_client(force_new=True)
            self.client.report({
                'api_id': '1',
                'elapse': '1'
            })


if __name__ == '__main__':
    unittest.main()
