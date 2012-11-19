import os
import sys

from mmstats import models, libgettid


def test_defaults():
    """Threadsafe defaults in expanded filename"""
    fn = models._expand_filename()
    assert str(os.getpid()) in fn, 'missing PID'
    assert str(libgettid.gettid()) in fn, 'missing TID'
    assert fn.endswith('.mmstats'), 'missing .mmstats extension'


def test_substitutions():
    fn = models._expand_filename(filename=' {CMD} {CMD} {PID} {TID}').split()
    cmd = os.path.basename(sys.argv[0])
    assert fn[1] == cmd, fn[1] + ' != ' + cmd
    assert fn[1] == fn[2], 'unable to repeat substitutions'
    assert fn[3] == str(os.getpid()), 'PID wrong'
    assert fn[4] == str(libgettid.gettid()), 'TID wrong'
