from . import base

import ctypes
import os

import mmstats


class TestMmap(base.MmstatsTestCase):

    def test_pagesize(self):
        """PAGESIZE > 0"""
        self.assertTrue(mmstats.PAGESIZE > 0, mmstats.PAGESIZE)

    def test_init_alt_name(self):
        expected_fn = os.path.join(self.path, 'mmstats-test_init_alt_name')
        self.assertFalse(os.path.exists(expected_fn))

        _, fn, sz, m = mmstats._init_mmap(
                path=self.path, filename='mmstats-test_init_alt_name')
        self.assertEqual(fn, expected_fn)
        self.assertTrue(os.path.exists(fn))

    def test_size_adjusting1(self):
        """mmapped files must be at least PAGESIZE in size"""
        _, _, sz, m = mmstats._init_mmap(path=self.path,
                filename='mmstats-test_size_adjusting-1', size=1)

        self.assertEqual(sz, mmstats.PAGESIZE)
        for i in range(sz):
            self.assertEqual(ctypes.c_char.from_address(m+i).value, '\x00')

    def test_size_adjusting2(self):
        """mmapped files must be multiples of PAGESIZE"""
        _, _, sz, m = mmstats._init_mmap(
                path=self.path,
                filename='mmstats-test_size_adjusting-2',
                size=(mmstats.PAGESIZE+1)
            )

        self.assertEqual(sz, mmstats.PAGESIZE * 2)
        for i in range(sz):
            self.assertEqual(ctypes.c_char.from_address(m+i).value, '\x00')

    def test_truncate(self):
        """mmapped files must be initialized with null bytes"""
        _, fn, sz, m = mmstats._init_mmap(
                path=self.path,
                filename='mmstats-test_truncate',
            )

        first_byte = ctypes.c_char.from_address(m)
        first_byte.value = 'X'

        reopened_file = open(fn)
        self.assertEqual(reopened_file.read(1), 'X')
        self.assertEqual(reopened_file.read(1), '\x00')

    def test_remove(self):
        """Calling remove() on an MmStat instance should remove the file"""
        class TestStat(mmstats.MmStats):
            b = mmstats.BoolField()

        fn = os.path.join(self.path, 'mmstats-test_remove')
        ts = TestStat(filename=fn)
        ts.b = True
        self.assertTrue(ts.b)
        self.assertTrue(os.path.exists(fn))
        ts.remove()
        self.assertFalse(os.path.exists(fn))
        # Trying to access the mmap after it's been removed should raise an
        # exception but *not* segault
        self.assertRaises(Exception, getattr, ts, 'b')
