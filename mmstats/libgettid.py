import ctypes
import os
import sys
import threading


def _linux_gettid():
    """Return system thread id or pid in single thread process"""
    return _libgettid.gettid()


def _universal_gettid():
    """Give up and just use Python's threading ident

    Some platforms erroneously return None for the main thread's ident. This
    will return 0 instead.
    """
    return threading.current_thread().ident or 0


if 'linux' in sys.platform:
    try:
        _PATH = os.path.dirname(os.path.abspath(__file__))
        _libgettid = ctypes.cdll.LoadLibrary(
                os.path.join(_PATH, '_libgettid.so'))
        _libgettid.gettid.restype = ctypes.c_int
        _libgettid.gettid.argtypes = []
    except:
        gettid = _universal_gettid
    else:
        gettid = _linux_gettid
else:
    gettid = _universal_gettid
