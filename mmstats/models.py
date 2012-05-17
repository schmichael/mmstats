import ctypes
import os
import sys
import time

from . import fields, libgettid, _mmap
from .defaults import DEFAULT_PATH, DEFAULT_FILENAME


class FieldState(object):
    """Holds field state for each Field instance"""

    def __init__(self, field):
        self.field = field


#TODO Rename to ???? ... MmStatsModel, MetricsModel ?
class FieldGroups(object):
    def __init__(self, stats_class, groups, path=DEFAULT_PATH,
            filename=DEFAULT_FILENAME):
        self._removed = False
        self._groups = {}
        self._size = 1

        # Initialize group instances
        for group_name in groups:
            group_inst = stats_class(group_name)
            self._groups[group_name] = group_inst
            self._size += group_inst.size

        self._fd, self._filename, self._size, self._mm_ptr = _mmap.init_mmap(
            path=path, filename=filename, size=self._size)
        mmap_t = ctypes.c_char * self._size

        # pointer to the entire mmap'd region
        self._mmap = mmap_t.from_address(self._mm_ptr)

        # First byte of the mmap'd region as a byte for the version number
        ver = ctypes.c_byte.from_address(self._mm_ptr)
        ver.value = 2  # Version number

        # Setup fields now that the size is calculated and mmap initialized
        offset = 1
        for group in self._groups.values():
            # Finally initialize thes stats
            group._init_fields(self._mm_ptr, offset)
            offset += group.size

    def __getattr__(self, group_name):
        if group_name in self._groups:
            return self._groups[group_name]
        else:
            raise AttributeError

    @property
    def filename(self):
        return self._filename

    @property
    def size(self):
        return self._size

    def flush(self, async=False):
        """Flush mmapped file to disk"""
        _mmap.msync(self._mm_ptr, self._size, async)

    def remove(self):
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


#TODO Rename to Template, MetricsTemplate, or Recipe
#TODO Add build(groups=[...]) class method (maybe builder() to return a
#     decorator)
class BaseMmStats(object):
    """Stats models should inherit from this"""

    def __init__(self, group):
        self.group = group

        # Store state for this instance's fields
        self._fields = {}

        self._size = 0
        #FIXME This is the *wrong* way to initialize stat fields
        for cls in self.__class__.__mro__:
            for attrname, attrval in cls.__dict__.items():
                if (attrname not in self._fields
                        and isinstance(attrval, fields.Field)):
                    self._size += self._add_field(attrname, attrval)

    def _add_field(self, name, field):
        """Given a name and Field instance, add this field and retun size"""
        # Stats need a place to store their per Mmstats instance state
        state = self._fields[name] = FieldState(field)

        # Call field._new to determine size
        return field._new(state, self.group, name)

    def _init_fields(self, mm_ptr, offset):
        """Once all fields have been added, initialize them in mmap"""
        for state in self._fields.values():
            # 2nd Call field._init to initialize new stat
            offset = state.field._init(state, mm_ptr, offset)

    @property
    def size(self):
        return self._size


class MmStats(BaseMmStats):
    """Mmstats default model base class

    Just subclass, add your own fields, and instantiate:

    >>> from mmstats.models import MmStats
    >>> from mmstats.fields import CounterField
    >>> class MyStats(MmStats):
    ...     errors = CounterField()
    ...
    >>> stats = MyStats()
    >>> stats.errors.inc()
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
