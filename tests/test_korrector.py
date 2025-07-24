from unittest import TestCase

from korrector.korrector import korrect


class TestKorrector(TestCase):

    def test_korrect(self):
        korrect("./testdbs/database.sqlite", "./backups")
        assert True