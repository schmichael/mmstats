from . import base

import ctypes
import os

import mmstats
from mmstats import _mmap


class TestMmap(base.MmstatsTestCase):

    def test_pagesize(self):
        """PAGESIZE > 0"""
        self.assertTrue(_mmap.PAGESIZE > 0, _mmap.PAGESIZE)

    def test_init_alt_name(self):
        expected_fn = os.path.join(self.path, 'mmstats-test_init_alt_name')
        self.assertFalse(os.path.exists(expected_fn))

        _, fn, sz, m = _mmap.init_mmap(
                path=self.path, filename='mmstats-test_init_alt_name')
        self.assertEqual(fn, expected_fn)
        self.assertTrue(os.path.exists(fn))

    def test_size_adjusting1(self):
        """mmapped files must be at least PAGESIZE in size"""
        _, _, sz, m = _mmap.init_mmap(path=self.path,
                filename='mmstats-test_size_adjusting-1', size=1)

        self.assertEqual(sz, _mmap.PAGESIZE)
        for i in range(sz):
            self.assertEqual(ctypes.c_char.from_address(m+i).value, '\x00')

    def test_size_adjusting2(self):
        """mmapped files must be multiples of PAGESIZE"""
        _, _, sz, m = _mmap.init_mmap(
                path=self.path,
                filename='mmstats-test_size_adjusting-2',
                size=(_mmap.PAGESIZE + 1)
            )

        self.assertEqual(sz, _mmap.PAGESIZE * 2)
        for i in range(sz):
            self.assertEqual(ctypes.c_char.from_address(m+i).value, '\x00')

    def test_truncate(self):
        """mmapped files must be initialized with null bytes"""
        _, fn, sz, m = _mmap.init_mmap(
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
        self.assertTrue(os.path.exists(fn), fn)
        ts.remove()
        self.assertFalse(os.path.exists(fn))
        # Trying to access the mmap after it's been removed should raise an
        # exception but *not* segault
        self.assertRaises(Exception, getattr, ts, 'b')
