from . import base

import os

import mmstats


class TestMmap(base.MmstatsTestCase):

    def test_pagesize(self):
        """PAGESIZE > 0"""
        self.assertTrue(mmstats.PAGESIZE > 0, mmstats.PAGESIZE)

    def test_init_alt_name(self):
        expected_fn = os.path.join(self.path, 'mmstats-test_init_alt_name')
        self.assertFalse(os.path.exists(expected_fn))

        fn, sz, m = mmstats._init_mmap(
                path=self.path, filename='mmstats-test_init_alt_name')
        self.assertEqual(fn, expected_fn)
        self.assertTrue(os.path.exists(fn))
