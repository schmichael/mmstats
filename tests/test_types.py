from . import base

import mmstats


class TestTypes(base.MmstatsTestCase):
    def test_ints(self):
        class MyStats(mmstats.MmStats):
            zebras = mmstats.IntField()
            apples = mmstats.UIntField()
            oranges = mmstats.UIntField()

        mmst = MyStats(filename='mmstats-test-ints')

        # Basic format
        self.assertEqual(mmst._mmap[0], '\x01')
        self.assertTrue('apples\x01\x00I' in mmst._mmap.raw)
        self.assertTrue('oranges\x01\x00I' in mmst._mmap.raw)
        self.assertTrue('zebras\x01\x00i' in mmst._mmap.raw)

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
        class ShortFields(mmstats.MmStats):
            a = mmstats.ShortField()
            b = mmstats.UShortField()

        s = ShortFields(filename='mmstats-test-shorts')
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
        class BoolFields(mmstats.MmStats):
            a = mmstats.BoolField()
            b = mmstats.BoolField(initial=True)

        s = BoolFields(filename='mmstats-test-bools')
        self.assertTrue('a\x01\x00?\xff\x00' in s._mmap[:], repr(s._mmap[:30]))
        self.assertTrue('b\x01\x00?\xff\x01' in s._mmap[:], repr(s._mmap[:30]))
        self.assertTrue(s.a is False, s.a)
        self.assertTrue(s.b is True, s.b)
        s.a = 'Anything truthy at all'
        self.assertTrue(s.a is True, s.a)
        self.assertTrue(s.b is True, s.b)
        s.a = [] # Anything falsey
        self.assertTrue(s.a is False, s.a)
        self.assertTrue(s.b is True, s.b)
        s.b = False
        s.a = s.b
        self.assertTrue(s.a is False, s.a)
        self.assertTrue(s.b is False, s.b)

    def test_strings(self):
        class StringStats(mmstats.BaseMmStats):
            a = mmstats.StaticTextField(label="text", value="something cool")
        m1 = StringStats(filename='mmstats-test-m1')

        self.assertTrue(m1.a, 'something cool')

    def test_mixed(self):
        class MixedStats(mmstats.MmStats):
            a = mmstats.UIntField()
            b = mmstats.BoolField()
            c = mmstats.IntField()
            d = mmstats.BoolField(label='The Bool')
            e = mmstats.ShortField(label='shortie')

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

    def test_counter(self):
        class SimpleCounter(mmstats.MmStats):
            counter = mmstats.CounterField()

        s = SimpleCounter(filename='mmstats-test_counter')
        self.assertEqual(s.counter.value, 0)
        s.counter.inc()
        self.assertEqual(s.counter.value, 1)
        s.counter.inc()
        self.assertEqual(s.counter.value, 2)
        s.counter.inc()
        self.assertEqual(s.counter.value, 3)
        s.counter.inc(-4)
        self.assertNotEqual(s.counter.value, -1)
        self.assertNotEqual(s.counter.value, 0)
        s.counter.value = 0
        self.assertEqual(s.counter.value, 0)

    def test_floats(self):
        class FloatTest(mmstats.MmStats):
            f = mmstats.FloatField()
            d = mmstats.DoubleField()

        ft = FloatTest(filename='mmstats-test_floats')
        self.assertEqual(ft.f, 0.0)
        self.assertEqual(ft.d, 0.0)
        ft.d = ft.f = 1.0
        self.assertEqual(ft.f, 1.0)
        self.assertEqual(ft.d, 1.0)
        ft.d = ft.f = -1.0
        self.assertEqual(ft.f, -1.0)
        self.assertEqual(ft.d, -1.0)
        ft.d = ft.f = 1.0 / 3
        self.assertTrue(ft.f > 0.3)
        self.assertTrue(ft.d > 0.3)
        self.assertTrue(ft.f < 0.4)
        self.assertTrue(ft.d < 0.4)


    def test_running_average(self):
        class RATest(mmstats.MmStats):
            avg = mmstats.RunningAverageField()
        rat = RATest(filename='mmstats-test_running_average')
        self.assertEqual(rat.avg.value, 0.0)
        rat.avg.add(1)
        self.assertEqual(rat.avg.value, 1.0)
        rat.avg.add(1)
        self.assertEqual(rat.avg.value, 1.0)
        rat.avg.add(1)
        self.assertEqual(rat.avg.value, 1.0)
        rat.avg.add(-3)
        self.assertEqual(rat.avg.value, 0.0)
        rat.avg.add(1)
        self.assertTrue(0 < rat.avg.value < 1)
