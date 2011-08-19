import glob
import os
import tempfile


def setUp():
    """Cleanup files on setup so you can inspect files after tests run"""
    tempdir = tempfile.gettempdir()
    mmstats_test_files = os.path.join(tempdir, 'mmstats-tests-*')
    for fn in glob.glob(mmstats_test_files):
        try:
            os.unlink(fn)
        except OSError:
            print 'Unable to remove test file: %s' % fn
