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

        a = LaserStats(filename='test-laserstats-a.mmstats')
        b = LaserStats(filename='test-laserstats-b.mmstats')

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

        stats = set()
        insts = {}

        s = ScienceStats(filename='test-tls-{TID}.mmstats')
        num_threads = 111
        ready = threading.Event()

        # Make it a mutable object (dict) instead of a bool so we can access it
        # inside the thread easily
        collision = {'status': False}

        class T(threading.Thread):
            def run(self):
                if s.filename in stats:
                    collision['status'] = True
                else:
                    stats.add(s.filename)

                # This is kind of silly, but would catch the case of a single
                # mmap being shared between threads
                insts[self.ident] = s.facts = str(uuid.uuid4())

                # Wait for all threads to be started before completing
                # If we don't do this, thread.idents will be reused
                ready.wait()

        threads = [T() for _ in range(num_threads)]

        for t in threads:
            t.start()

        ready.set()  # go!

        for t in threads:
            t.join()

        self.assertFalse(collision['status'])
        self.assertEqual(len(stats), num_threads)
        self.assertEqual(len(insts), num_threads)
        self.assertEqual(len(set(insts.values())), num_threads)

    def test_label_prefix(self):
        class StatsA(mmstats.MmStats):
            f2 = mmstats.UIntField(label='f.secondary')
            f1 = mmstats.UIntField()

        a = StatsA(filename='test-label-prefix1.mmstats')
        b = StatsA(filename='test-label-prefix2.mmstats',
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

        bs = BigStats(filename='test-resize2.mmstats')
        self.assertEqual(bs.size, _mmap.PAGESIZE * 3)

    def test_mmap_resize2(self):
        class BigStats(mmstats.MmStats):
            f1 = mmstats.UIntField(label='f'+('o'*_mmap.PAGESIZE))
            f2 = mmstats.UIntField(label='f'+('0'*_mmap.PAGESIZE))
            f3 = mmstats.UIntField(label='f'+('1'*_mmap.PAGESIZE))

        bs = BigStats(filename='test-resize2.mmstats')
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
