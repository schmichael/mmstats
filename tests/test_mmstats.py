import mmstats


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
        f2 = mmstats.UIntStat(label='f.secondary')
        f1 = mmstats.UIntStat()

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
