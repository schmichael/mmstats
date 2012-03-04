import ctypes
import struct
import time

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

    def test_counter_sz(self):
        self.assertEquals(ctypes.sizeof(mmstats.CounterField.buffer_type), 8)
        self.assertEquals(
                struct.calcsize(mmstats.CounterField.type_signature), 8)

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

    def test_average(self):
        class AvgTest(mmstats.MmStats):
            avg = mmstats.AverageField()
        at = AvgTest(filename='mmstats-test_average')
        self.assertEqual(at.avg.value, 0.0)
        at.avg.add(1)
        self.assertEqual(at.avg.value, 1.0)
        at.avg.add(1)
        self.assertEqual(at.avg.value, 1.0)
        at.avg.add(1)
        self.assertEqual(at.avg.value, 1.0)
        at.avg.add(-3)
        self.assertEqual(at.avg.value, 0.0)
        at.avg.add(1)
        self.assertTrue(0 < at.avg.value < 1)

    def test_static_strings(self):
        class StaticStringStats(mmstats.BaseMmStats):
            a = mmstats.StaticTextField(label="text", value="something cool")
        m1 = StaticStringStats(filename='mmstats-test_strings_simple')

        self.assertTrue(m1.a, 'something cool')

    def test_strings(self):
        class StrTest(mmstats.MmStats):
            f = mmstats.FloatField()
            s = mmstats.StringField(10)
            c = mmstats.CounterField()
        st = StrTest(filename='mmstats-test_strings')
        self.assertEqual(st.f, 0.0)
        self.assertEqual(st.c.value, 0)
        self.assertEqual(st.s, '')
        st.s = 'a' * 11
        self.assertEqual(st.s, 'a' * 10)
        st.s = 'b'
        self.assertEqual(st.s, 'b')
        self.assertEqual(st.f, 0.0)
        self.assertEqual(st.c.value, 0)
        st.f = 1.0
        st.c.inc()
        self.assertEqual(st.s, 'b')
        self.assertEqual(st.f, 1.0)
        self.assertEqual(st.c.value, 1)
        st.s = u'\u2764' * 11
        # character is multibyte, so only 3 fit in 10 UTF8 encoded bytes
        self.assertEqual(st.s, u'\u2764' * 3)
        self.assertEqual(st.f, 1.0)
        self.assertEqual(st.c.value, 1)

    def test_moving_avg(self):
        class MATest(mmstats.MmStats):
            m1 = mmstats.MovingAverageField()
            a = mmstats.AverageField()
            m2 = mmstats.MovingAverageField()
        stats = MATest(filename='mmstats-test_moving_avg')
        self.assertEqual(stats.m1.value, 0.0)
        stats.m1.add(1)
        self.assertEqual(stats.m1.value, 1.0)
        stats.m1.add(2)
        self.assertEqual(stats.m1.value, 1.5)
        for i in range(1000):
            stats.m1.add(1)
            stats.a.add(i)
            stats.m2.add(i)
        self.assertEqual(stats.m1.value, 1.0)
        self.assertTrue(stats.a.value < stats.m2.value,
                '%d < %d' % (stats.a.value, stats.m2.value))

    def test_moving_avg_alt_sizes(self):
        class MATest2(mmstats.MmStats):
            m1 = mmstats.MovingAverageField(size=1)
            m2 = mmstats.MovingAverageField()
            m3 = mmstats.MovingAverageField(size=1000)
        stats = MATest2(filename='mmstats-test_moving_avg_alt_sizes')
        for i in range(1000):
            stats.m1.add(i)
            stats.m2.add(i)
            stats.m3.add(i)
        self.assertEqual(stats.m1.value, 999.0)
        self.assertTrue(stats.m1.value > stats.m2.value > stats.m3.value)
        for i in range(1000):
            stats.m1.add(i)
            stats.m2.add(i)
            stats.m3.add(i)
        self.assertEqual(stats.m1.value, 999.0)
        self.assertTrue(stats.m1.value > stats.m2.value > stats.m3.value)

    def test_timer(self):
        class TTest(mmstats.MmStats):
            m1 = mmstats.MovingAverageField()
            t1 = mmstats.TimerField()
            c = mmstats.CounterField()
            t2 = mmstats.TimerField(timer=time.clock)
        stats = TTest(filename='mmstats-test_timer')
        with stats.t1 as timer:
            # Timer's value should == 0 until this context exits
            self.assertEqual(stats.t1.value, 0.0)
            self.assertEqual(stats.t2.value, 0.0)
            self.assertEqual(stats.t2.last, 0.0)
            # Some time has passed
            self.assertTrue(timer.elapsed > 0.0)
            e = timer.elapsed
            # Any later elapsed check should be > than the former
            self.assertTrue(timer.elapsed > e)
        self.assertNotEqual(stats.t1.value, stats.t2.value)
        self.assertEqual(stats.t1.value, stats.t1.last)
        oldval = stats.t1.value
        last = stats.t1.last
        stats.t1.start()
        stats.t1.stop()
        self.assertTrue(stats.t1.last < last)
        self.assertTrue(stats.t1.value < oldval)
