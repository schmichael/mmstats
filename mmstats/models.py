import ctypes
import glob
import os
import sys
import time
import threading

from . import fields, libgettid, _mmap
from .defaults import DEFAULT_PATH, DEFAULT_FILENAME


removal_lock = threading.Lock()


def _expand_filename(path=DEFAULT_PATH, filename=DEFAULT_FILENAME):
    """Compute mmap's full path given a `path` and `filename`.

    :param path: path to store mmaped files
    :param filename: filename template for mmaped files
    :returns: fully expanded path and filename
    :rtype: str

    Substitutions documented in :class:`~mmstats.models.BaseMmStats`
    """
    substitutions = {
        'CMD': os.path.basename(sys.argv[0]),
        'PID': os.getpid(),
        'TID': libgettid.gettid(),
    }
    # Format filename and path with substitution variables
    filename = filename.format(**substitutions)
    path = path.format(**substitutions)

    return os.path.join(path, filename)


class FieldState(object):
    """Holds field state for each Field instance"""

    def __init__(self, field):
        self.field = field


class BaseMmStats(threading.local):
    """Stats models should inherit from this

    Optionally given a filename or label_prefix, create an MmStats instance

    Both `filename` and `path` support the following variable substiutions:

    * `{CMD}` - name of application (`os.path.basename(sys.argv[0])`)
    * `{PID}` - process's PID (`os.getpid()`)
    * `{TID}` - thread ID (tries to get it via the `SYS_gettid` syscall but
      fallsback to the Python/pthread ID or 0 for truly broken platforms)

    This class is *not threadsafe*, so you should include both {PID} and
    {TID} in your filename to ensure the mmaped files don't collide.
    """

    def __init__(self, path=DEFAULT_PATH, filename=DEFAULT_FILENAME,
                 label_prefix=None):
        self._removed = False

        # Setup label prefix
        self._label_prefix = '' if label_prefix is None else label_prefix

        self._full_path = _expand_filename(path, filename)
        self._filename = filename
        self._path = path

        self._offset = 1

        # Store state for this instance's fields
        self._fields = {}

        total_size = self._offset
        #FIXME This is the *wrong* way to initialize stat fields
        for cls in self.__class__.__mro__:
            for attrname, attrval in cls.__dict__.items():
                if (attrname not in self._fields
                        and isinstance(attrval, fields.Field)):
                    total_size += self._add_field(attrname, attrval)

        self._fd, self._size, self._mm_ptr = _mmap.init_mmap(
            self._full_path, size=total_size)
        mmap_t = ctypes.c_char * self._size
        self._mmap = mmap_t.from_address(self._mm_ptr)
        ver = ctypes.c_byte.from_address(self._mm_ptr)
        ver.value = 1  # Version number

        # Finally initialize thes stats
        self._init_fields(total_size)

    def _add_field(self, name, field):
        """Given a name and Field instance, add this field and retun size"""
        # Stats need a place to store their per Mmstats instance state
        state = self._fields[name] = FieldState(field)

        # Call field._new to determine size
        return field._new(state, self.label_prefix, name)

    def _init_fields(self, total_size):
        """Once all fields have been added, initialize them in mmap"""

        for state in self._fields.values():
            # 2nd Call field._init to initialize new stat
            self._offset = state.field._init(state, self._mm_ptr, self._offset)

    @property
    def filename(self):
        return self._full_path

    @property
    def label_prefix(self):
        return self._label_prefix

    @property
    def size(self):
        return self._size

    def flush(self, async=False):
        """Flush mmapped file to disk

        :param async: ``True`` means the call won't wait for the flush to
                      finish syncing to disk. Defaults to ``False``
        :type async: bool
        """
        _mmap.msync(self._mm_ptr, self._size, async)

    def remove(self):
        with removal_lock:
            # Perform regular removal of this process/thread's own file.
            self._remove()
            # Then ensure we clean up any forgotten thread-related files, if
            # applicable. Ensure {PID} exists, for safety's sake - better to not
            # cleanup than to cleanup multiple PIDs' files.
            if '{PID}' in self._filename and '{TID}' in self._filename:
                self._remove_stale_thread_files()

    def _remove_stale_thread_files(self):
        # The originally given (to __init__) filename string, containing
        # expansion hints, is preserved in _filename. If it contains {TID} we
        # can replace that with a glob expression to catch all TIDS for our
        # given PID.
        globbed = self._filename.replace('{TID}', '*')
        # Re-expand any non-{TID} expansion hints
        expanded = _expand_filename(path=self._path, filename=globbed)
        # And nuke as appropriate.
        for leftover in glob.glob(expanded):
            os.remove(leftover)

    def _remove(self):
        """Close and remove mmap file - No further stats updates will work"""
        if self._removed:
            # Make calling more than once a noop
            return
        _mmap.munmap(self._mm_ptr, self._size)
        self._size = None
        self._mm_ptr = None
        self._mmap = None
        os.close(self._fd)
        try:
            os.remove(self.filename)
        except OSError:
            # Ignore failed file removals
            pass
        # Remove fields to prevent segfaults
        self._fields = {}
        self._removed = True


class MmStats(BaseMmStats):
    """Mmstats default model base class

    Just subclass, add your own fields, and instantiate:

    >>> from mmstats.models import MmStats
    >>> from mmstats.fields import CounterField
    >>> class MyStats(MmStats):
    ...     errors = CounterField()
    ...
    >>> stats = MyStats()
    >>> stats.errors.incr()
    >>> stats.errors.value
    1L
    """
    pid = fields.StaticUIntField(label="sys.pid", value=os.getpid)
    tid = fields.StaticInt64Field(label="sys.tid", value=libgettid.gettid)
    uid = fields.StaticUInt64Field(label="sys.uid", value=os.getuid)
    gid = fields.StaticUInt64Field(label="sys.gid", value=os.getgid)
    python_version = fields.StaticTextField(label="org.python.version",
            value=lambda: sys.version.replace("\n", ""))
    created = fields.StaticDoubleField(label="sys.created", value=time.time)
