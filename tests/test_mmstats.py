import glob
import os
import tempfile

import mmstats


def setUp():
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
