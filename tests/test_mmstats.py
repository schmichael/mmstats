import glob
import os
import tempfile

import mmstats


def setUp():
    """Cleanup files on setup so you can inspect files after tests run"""
    tempdir = tempfile.gettempdir()
    mmstats_test_files = os.path.join(tempdir, 'mmstats-tests-')
    for fn in glob.glob(mmstats_test_files):
        try:
            os.unlink(fn)
        except OSError:
            print 'Unable to remove test file: %s' % fn


def test_uint():
    class MyStats(mmstats.MmStats):
        zebras = mmstats.UIntStat()
        apples = mmstats.UIntStat()
        oranges = mmstats.UIntStat()

    mmst = MyStats()

    # Basic format
    assert mmst._mmap[0] == '\x01'
    assert mmst._mmap.find('applesI') != -1
    assert mmst._mmap.find('orangesI') != -1
    assert mmst._mmap.find('zebrasI') != -1

    # Stat manipulation
    assert mmst.apples == 0
    assert mmst.oranges == 0
    assert mmst.zebras == 0

    mmst.apples = 1
    assert mmst.apples == 1
    assert mmst.oranges == 0
    assert mmst.zebras == 0

    mmst.zebras = 9001
    assert mmst.apples == 1
    assert mmst.oranges == 0
    assert mmst.zebras == 9001


def test_class_instances():
    """You can have 2 instances of an MmStats model without shared state"""
    class LaserStats(mmstats.MmStats):
        blue = mmstats.UIntStat()
        red = mmstats.UIntStat()

    a = LaserStats(filename='mmstats-test-laserstats-a')
    b = LaserStats(filename='mmstats-test-laserstats-b')

    a.blue = 1
    a.red = 2
    b.blue = 42

    assert a.blue == 1
    assert a.red == 2
    assert b.blue == 42
    assert b.red == 0


def test_label_prefix():
    class StatsA(mmstats.MmStats):
        f1 = mmstats.UIntStat()
        f2 = mmstats.UIntStat(label='f.secondary')

    a = StatsA(filename='mmstats-test-label-prefix1')
    b = StatsA(filename='mmstats-test-label-prefix2',
            label_prefix='org.mmstats.')

    assert 'f1I' in a._mmap[:]
    assert 'f.secondaryI' in a._mmap[:]
    assert 'org.mmstats.' not in a._mmap[:]
    assert 'org.mmstats.f1I' in b._mmap[:]
    assert 'org.mmstats.f.secondaryI' in b._mmap[:]

    # Attributes should be unaffected
    a.f1 = 2
    b.f1 = 3
    a.f2 = 4
    b.f2 = 5

    assert a.f1 == 2
    assert b.f1 == 3
    assert a.f2 == 4
    assert b.f2 == 5
