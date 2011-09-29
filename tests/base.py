import unittest

import glob
import os


os.environ.setdefault('MMSTATS_PATH', '.')


class MmstatsTestCase(unittest.TestCase):
    def setUp(self):
        super(MmstatsTestCase, self).setUp()
        self.path = os.environ['MMSTATS_PATH']

        # Clean out stale mmstats files
        for fn in glob.glob('./mmstats-test*'):
            try:
                os.remove(fn)
            except OSError:
                print 'Could not remove: %s' % fn

    def tearDown(self):
        # clean the dir after tests
        for fn in glob.glob('./mmstats-test*'):
            try:
                os.remove(fn)
            except OSError:
                continue
