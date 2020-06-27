import unittest
import warnings
from os import remove
from os.path import isfile

from docbooktoxtm import __version__
from docbooktoxtm.functions import get_zip

course = 'DTX123'
user = 'raorourke'
token = None
release_tag = __version__


def ignore_warnings(func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ResourceWarning)
            func(self, *args, **kwargs)

    return do_test


@ignore_warnings
class TestGetZip(unittest.TestCase):
    def test_get_zip(self):
        self.zipf = get_zip(course, release_tag, user, token)
        self.assertTrue(isfile(self.zipf))

    def tearDown(self):
        super(TestGetZip, self).tearDown()
        remove(self.zipf)


if __name__ == '__main__':
    unittest.main()