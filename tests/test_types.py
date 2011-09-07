from . import base

import mmstats


class TestTypes(base.MmstatsTestCase):
    def test_ints(self):
        class MyStats(mmstats.MmStats):
            zebras = mmstats.IntStat()
            apples = mmstats.UIntStat()
            oranges = mmstats.UIntStat()

        mmst = MyStats(filename='mmstats-test-ints')

        # Basic format
        self.assertEqual(mmst._mmap[0], '\x01')
        self.assertNotEqual(mmst._mmap.find('applesI'), -1)
        self.assertNotEqual(mmst._mmap.find('orangesI'), -1)
        self.assertNotEqual(mmst._mmap.find('zebrasi'), -1)

        # Stat manipulation
        self.assertEqual(mmst.apples, 0)
        self.assertEqual(mmst.oranges, 0)
        self.assertEqual(mmst.zebras, 0)

        mmst.apples = 1
        self.assertEqual(mmst.apples, 1)
        self.assertEqual(mmst.oranges, 0)
        self.assertEqual(mmst.zebras, 0)

        mmst.zebras = -9001
        self.assertEqual(mmst.apples, 1)
        self.assertEqual(mmst.oranges, 0)
        self.assertEqual(mmst.zebras, -9001)

        mmst.apples = -100
        self.assertEqual(mmst.apples, (2**32)-100)

    def test_shorts(self):
        class ShortStats(mmstats.MmStats):
            a = mmstats.ShortStat()
            b = mmstats.UShortStat()

        s = ShortStats(filename='mmstats-test-shorts')
        self.assertEqual(s.a, 0, s.a)
        self.assertEqual(s.b, 0, s.b)
        s.a = -1
        self.assertEqual(s.a, -1, s.a)
        self.assertEqual(s.b, 0, s.b)
        s.b = (2**16)-1
        self.assertEqual(s.a, -1, s.a)
        self.assertEqual(s.b, (2**16)-1, s.b)
        s.b = -2
        self.assertEqual(s.a, -1, s.a)
        self.assertEqual(s.b, (2**16)-2, s.b)

    def test_bools(self):
        class BoolStats(mmstats.MmStats):
            a = mmstats.BoolStat()
            b = mmstats.BoolStat()

        s = BoolStats(filename='mmstats-test-bools')
        self.assertTrue('a?\xff\x00' in s._mmap[:], repr(s._mmap[:30]))
        self.assertTrue('b?\xff\x00' in s._mmap[:], repr(s._mmap[:30]))
        self.assertTrue(s.a is False, s.a)
        self.assertTrue(s.b is False, s.b)
        s.a = 'Anything truthy at all'
        self.assertTrue(s.a is True, s.a)
        self.assertTrue(s.b is False, s.b)
        s.a = [] # Anything falsey
        self.assertTrue(s.a is False, s.a)
        self.assertTrue(s.b is False, s.b)
        s.b = 1
        s.a = s.b
        self.assertTrue(s.a is True, s.a)
        self.assertTrue(s.b is True, s.b)

    def test_mixed(self):
        class MixedStats(mmstats.MmStats):
            a = mmstats.UIntStat()
            b = mmstats.BoolStat()
            c = mmstats.IntStat()
            d = mmstats.BoolStat(label='The Bool')
            e = mmstats.ShortStat(label='shortie')

        m1 = MixedStats(label_prefix='m1::', filename='mmstats-test-m1')
        m2 = MixedStats(label_prefix='m2::', filename='mmstats-test-m2')

        self.assertTrue('m2::shortie' not in m1._mmap[:])
        self.assertTrue('m2::shortie' in m2._mmap[:], repr(m2._mmap[:40]))

        for i in range(10):
            m1.a = i
            m2.a = i * 2
            m1.b = True
            m2.b = False
            m1.c = -i
            m2.c = -i * 2
            m1.d = False
            m2.d = True
            m1.e = 1
            m2.e = i * 10

        self.assertEqual(m1.a, i, m1.a)
        self.assertEqual(m2.a, i * 2, m2.a)
        self.assertTrue(m1.b is True, m1.b)
        self.assertTrue(m2.b is False, m2.b)
        self.assertEqual(m1.c, -i, m1.c)
        self.assertEqual(m2.c, -i * 2, m2.c)
        self.assertTrue(m1.d is False, m1.d)
        self.assertTrue(m2.d is True, m2.d)
        self.assertEqual(m1.e, 1, m1.e)
        self.assertEqual(m2.e, 90, m2.e)
