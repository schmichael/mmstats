from . import base

import threading
import uuid

import mmstats
from mmstats import _mmap


class TestMmStats(base.MmstatsTestCase):
    def test_class_instances(self):
        """You can have 2 instances of an MmStats model without shared state"""
        class LaserStats(mmstats.MmStats):
            blue = mmstats.UIntField()
            red = mmstats.UIntField()

        a = LaserStats(filename='mmstats-test-laserstats-a')
        b = LaserStats(filename='mmstats-test-laserstats-b')

        a.blue = 1
        a.red = 2
        b.blue = 42

        self.assertEqual(a.blue, 1)
        self.assertEqual(a.red, 2)
        self.assertEqual(b.blue, 42)
        self.assertEqual(b.red, 0)

    def test_tls(self):
        """MmStats instances are unique per thread"""
        class ScienceStats(mmstats.MmStats):
            facts = mmstats.StringField(size=50)

        stats = {}

        def w(i):
            g = ScienceStats.create_getter(filename='mmstats-test-tls-%TID%')
            s = g()
            s.facts = str(uuid.uuid4())
            stats[i] = s

        threads = []

        for i in range(8):
            t = threading.Thread(target=w, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self.assertEqual(len(stats), 8)
        self.assertEqual(len(set(stats.values())), 8)

    def test_label_prefix(self):
        class StatsA(mmstats.MmStats):
            f2 = mmstats.UIntField(label='f.secondary')
            f1 = mmstats.UIntField()

        a = StatsA(filename='mmstats-test-label-prefix1')
        b = StatsA(filename='mmstats-test-label-prefix2',
                label_prefix='org.mmstats.')

        self.assertTrue('f1\x01\x00I' in a._mmap[:])
        self.assertTrue('f.secondary\x01\x00I' in a._mmap[:])
        self.assertTrue('org.mmstats.' not in a._mmap[:])
        self.assertTrue('org.mmstats.f1\x01\x00I' in b._mmap[:])
        self.assertTrue('org.mmstats.f.secondary\x01\x00I' in b._mmap[:])

        # Attributes should be unaffected
        a.f1 = 2
        b.f1 = 3
        a.f2 = 4
        b.f2 = 5

        self.assertEqual(a.f1, 2)
        self.assertEqual(b.f1, 3)
        self.assertEqual(a.f2, 4)
        self.assertEqual(b.f2, 5)

    def test_mmap_resize1(self):
        class BigStats(mmstats.MmStats):
            f1 = mmstats.BoolField(label='f1'*(_mmap.PAGESIZE / 2))
            f2 = mmstats.BoolField(label='f2'*(_mmap.PAGESIZE / 2))

        bs = BigStats(filename='mmstats-test-resize2')
        self.assertEqual(bs.size, _mmap.PAGESIZE * 3)

    def test_mmap_resize2(self):
        class BigStats(mmstats.MmStats):
            f1 = mmstats.UIntField(label='f'+('o'*_mmap.PAGESIZE))
            f2 = mmstats.UIntField(label='f'+('0'*_mmap.PAGESIZE))
            f3 = mmstats.UIntField(label='f'+('1'*_mmap.PAGESIZE))

        bs = BigStats(filename='mmstats-test-resize2')
        self.assertEqual(bs.size, _mmap.PAGESIZE * 4)
        self.assertEqual(bs.f1, 0)
        self.assertEqual(bs.f2, 0)
        self.assertEqual(bs.f3, 0)

    def test_subclassing(self):
        class ParentStats(mmstats.MmStats):
            a = mmstats.UIntField()
            b = mmstats.UIntField()

        class ChildAStats(ParentStats):
            a = mmstats.BoolField()
            c = mmstats.UIntField()

        class ChildBStats(ChildAStats):
            b = mmstats.BoolField()
            c = mmstats.BoolField()

        self.assertTrue(isinstance(ParentStats.a, mmstats.UIntField))
        self.assertTrue(isinstance(ParentStats.b, mmstats.UIntField))
        self.assertRaises(AttributeError, getattr, ParentStats, 'c')

        self.assertTrue(isinstance(ChildAStats.a, mmstats.BoolField))
        self.assertTrue(isinstance(ChildAStats.b, mmstats.UIntField))
        self.assertTrue(isinstance(ChildAStats.c, mmstats.UIntField))

        self.assertTrue(isinstance(ChildBStats.a, mmstats.BoolField))
        self.assertTrue(isinstance(ChildBStats.b, mmstats.BoolField))
        self.assertTrue(isinstance(ChildBStats.c, mmstats.BoolField))
