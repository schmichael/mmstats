import mmstats

def test_ints():
    class MyStats(mmstats.MmStats):
        zebras = mmstats.IntStat()
        apples = mmstats.UIntStat()
        oranges = mmstats.UIntStat()

    mmst = MyStats(filename='mmstats-test-ints')

    # Basic format
    assert mmst._mmap[0] == '\x01'
    assert mmst._mmap.find('applesI') != -1
    assert mmst._mmap.find('orangesI') != -1
    assert mmst._mmap.find('zebrasi') != -1

    # Stat manipulation
    assert mmst.apples == 0
    assert mmst.oranges == 0
    assert mmst.zebras == 0

    mmst.apples = 1
    assert mmst.apples == 1
    assert mmst.oranges == 0
    assert mmst.zebras == 0

    mmst.zebras = -9001
    assert mmst.apples == 1
    assert mmst.oranges == 0
    assert mmst.zebras == -9001

    mmst.apples = -100
    assert mmst.apples == (2**32)-100


def test_shorts():
    class ShortStats(mmstats.MmStats):
        a = mmstats.ShortStat()
        b = mmstats.UShortStat()

    s = ShortStats(filename='mmstats-test-shorts')
    assert s.a == 0, s.a
    assert s.b == 0, s.b
    s.a = -1
    assert s.a == -1, s.a
    assert s.b == 0, s.b
    s.b = (2**16)-1
    assert s.a == -1, s.a
    assert s.b == (2**16)-1, s.b
    s.b = -2
    assert s.a == -1, s.a
    assert s.b == (2**16)-2, s.b


def test_bools():
    class BoolStats(mmstats.MmStats):
        a = mmstats.BoolStat()
        b = mmstats.BoolStat()

    s = BoolStats(filename='mmstats-test-bools')
    assert 'a?\xff\x00' in s._mmap[:], repr(s._mmap[:30])
    assert 'b?\xff\x00' in s._mmap[:], repr(s._mmap[:30])
    assert s.a is False, s.a
    assert s.b is False, s.b
    s.a = 'Anything truthy at all'
    assert s.a is True, s.a
    assert s.b is False, s.b
    s.a = [] # Anything falsey
    assert s.a is False, s.a
    assert s.b is False, s.b
    s.b = 1
    s.a = s.b
    assert s.a is True, s.a
    assert s.b is True, s.b


def test_mixed():
    class MixedStats(mmstats.MmStats):
        a = mmstats.UIntStat()
        b = mmstats.BoolStat()
        c = mmstats.IntStat()
        d = mmstats.BoolStat(label='The Bool')
        e = mmstats.ShortStat(label='shortie')

    m1 = MixedStats(label_prefix='m1::', filename='mmstats-test-m1')
    m2 = MixedStats(label_prefix='m2::', filename='mmstats-test-m2')

    assert 'm2::shortie' not in m1._mmap[:]
    assert 'm2::shortie' in m2._mmap[:], repr(m2._mmap[:40])

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

    assert m1.a == i, m1.a
    assert m2.a == i * 2, m2.a
    assert m1.b is True, m1.b
    assert m2.b is False, m2.b
    assert m1.c == -i, m1.c
    assert m2.c == -i * 2, m2.c
    assert m1.d is False, m1.d
    assert m2.d is True, m2.d
    assert m1.e == 1, m1.e
    assert m2.e == 90, m2.e
