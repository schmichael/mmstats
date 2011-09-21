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

    def test_size_adjusting1(self):
        """mmapped files must be at least PAGESIZE in size"""
        _, sz, m = mmstats._init_mmap(path=self.path,
                filename='mmstats-test_size_adjusting-1', size=1)

        self.assertEqual(sz, mmstats.PAGESIZE)
        self.assertEqual(m[:], '\x00' * mmstats.PAGESIZE)

    def test_size_adjusting2(self):
        """mmapped files must be multiples of PAGESIZE"""
        _, sz, m = mmstats._init_mmap(
                path=self.path,
                filename='mmstats-test_size_adjusting-2',
                size=(mmstats.PAGESIZE+1)
            )

        self.assertEqual(sz, mmstats.PAGESIZE * 2)
        self.assertEqual(m[:], '\x00' * mmstats.PAGESIZE * 2)

    def test_truncate(self):
        """mmapped files must be initialized with null bytes"""
        fn, sz, m = mmstats._init_mmap(
                path=self.path,
                filename='mmstats-test_truncate',
            )

        m[0] = 'X'

        reopened_file = open(fn)
        self.assertEqual(reopened_file.read(1), 'X')
        self.assertEqual(reopened_file.read(1), '\x00')
