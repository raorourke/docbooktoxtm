import unittest
import warnings

import github

from docbooktoxtm import __version__

test_repo = 'raorourke/DTX123'
release_tag = __version__


def ignore_warnings(func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ResourceWarning)
            func(self, *args, **kwargs)

    return do_test


@ignore_warnings
class TestGitHub(unittest.TestCase):

    def setUp(self):
        super(TestGitHub, self).setUp()
        self.g = github.Github()
        self.repo = self.g.get_repo(test_repo)
        self.latest_release = self.repo.get_latest_release()

    def test_g(self):
        self.assertIsInstance(self.g, github.MainClass.Github)

    def test_repo(self):
        self.assertIsInstance(self.repo, github.Repository.Repository)

    def test_release(self):
        self.assertIsInstance(self.latest_release, github.GitRelease.GitRelease)

    def tearDown(self):
        super(TestGitHub, self).tearDown()
        self.g = None
        self.repo = None
        self.latest_release = None


if __name__ == '__main__':
    unittest.main()
