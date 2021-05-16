import unittest


class ExampleTest(unittest.TestCase):
    def setUp(self):
        self.cid = 1

    def test_sample(self):
        self.assertEqual(1, self.cid)
