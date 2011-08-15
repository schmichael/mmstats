import mmstats

def test_uint():
    class MyStats(mmstats.MmStats):
        zebras = mmstats.UIntStat()
        apples = mmstats.UIntStat()
        oranges = mmstats.UIntStat()

    mmst = MyStats()

    # Basic format
    assert mmst.mmap[0] == '\x01'
    assert mmst.mmap.find('applesL') != -1
    assert mmst.mmap.find('orangesL') != -1
    assert mmst.mmap.find('zebrasL') != -1

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
