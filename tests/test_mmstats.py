from . import base

import mmstats


class TestMmStats(base.MmstatsTestCase):
    def test_class_instances(self):
        """You can have 2 instances of an MmStats model without shared state"""
        class LaserStats(mmstats.MmStats):
            blue = mmstats.UIntStat()
            red = mmstats.UIntStat()

        a = LaserStats(filename='mmstats-test-laserstats-a')
        b = LaserStats(filename='mmstats-test-laserstats-b')

        a.blue = 1
        a.red = 2
        b.blue = 42

        self.assertEqual(a.blue, 1)
        self.assertEqual(a.red, 2)
        self.assertEqual(b.blue, 42)
        self.assertEqual(b.red, 0)

    def test_label_prefix(self):
        class StatsA(mmstats.MmStats):
            f2 = mmstats.UIntStat(label='f.secondary')
            f1 = mmstats.UIntStat()

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
            f1 = mmstats.BoolStat(label='f1'*(mmstats.PAGESIZE / 2))
            f2 = mmstats.BoolStat(label='f2'*(mmstats.PAGESIZE / 2))

        bs = BigStats()
        self.assertEqual(bs.size, mmstats.PAGESIZE * 3)

    def test_mmap_resize2(self):
        class BigStats(mmstats.MmStats):
            f1 = mmstats.UIntStat(label='f'+('o'*mmstats.PAGESIZE))
            f2 = mmstats.UIntStat(label='f'+('0'*mmstats.PAGESIZE))
            f3 = mmstats.UIntStat(label='f'+('1'*mmstats.PAGESIZE))

        bs = BigStats(filename='mmstats-test-resize1')
        self.assertEqual(bs.size, mmstats.PAGESIZE * 4)
        self.assertEqual(bs.f1, 0)
        self.assertEqual(bs.f2, 0)
        self.assertEqual(bs.f3, 0)
