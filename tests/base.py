import unittest

import glob
import os

import mmstats


class MmstatsTestCase(unittest.TestCase):
    def setUp(self):
        super(MmstatsTestCase, self).setUp()
        self.path = mmstats.DEFAULT_PATH

        # Clean out stale mmstats files
        for fn in glob.glob(os.path.join(self.path, 'test*.mmstats')):
            try:
                os.remove(fn)
                pass
            except OSError:
                print 'Could not remove: %s' % fn

    def tearDown(self):
        # clean the dir after tests
        for fn in glob.glob(os.path.join(self.path, 'test*.mmstats')):
            try:
                os.remove(fn)
                pass
            except OSError:
                continue
