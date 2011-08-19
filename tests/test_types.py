import mmstats

def test_ints():
    class MyStats(mmstats.MmStats):
        zebras = mmstats.IntStat()
        apples = mmstats.UIntStat()
        oranges = mmstats.UIntStat()

    mmst = MyStats(filename='mmstats-test-ints')

    # Basic format
    assert mmst._mmap[0] == '\x01'
    assert mmst._mmap.find('applesL') != -1
    assert mmst._mmap.find('orangesL') != -1
    assert mmst._mmap.find('zebrasl') != -1

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
