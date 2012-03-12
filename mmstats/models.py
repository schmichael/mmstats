import ctypes
import os
import sys
import time

from . import fields, libgettid, _mmap
from .defaults import DEFAULT_PATH, DEFAULT_FILENAME


class OutOfSpaceError(Exception):
    """No more room in mmap for extra fields"""


class NameCollisionError(Exception):
    """Attribute already exists with field name specified"""


class FieldState(object):
    """Holds field state for each Field instance"""

    def __init__(self, field):
        self.field = field


class BaseMmStats(object):
    """Stats models should inherit from this"""

    def __init__(self, path=DEFAULT_PATH, filename=DEFAULT_FILENAME,
            label_prefix=None, extra_space=0):
        """\
        Create an MmStats instance (instances are *not* threadsafe)

        Optionally give a ``filename`` and/or ``path`` to control where the
        mmap files are created.

        ``label_prefix`` will be prepended to all field names.

        ``extra_space`` is the amount of extra space in bytes to leave at the
        end of the mmap region. Specify this if you dynamically add fields.
        """
        self._removed = False

        # Setup label prefix
        self._label_prefix = '' if label_prefix is None else label_prefix

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

        # Add in free_space before creating mmap
        total_size += extra_space

        # Create mmap
        self._fd, self._filename, self._size, self._mm_ptr = _mmap.init_mmap(
            path=path, filename=filename, size=total_size)
        mmap_t = ctypes.c_char * self._size
        self._mmap = mmap_t.from_address(self._mm_ptr)
        ver = ctypes.c_byte.from_address(self._mm_ptr)
        ver.value = 1  # Version number

        # Finally initialize the stats
        self._init_fields()

    def add_field(self, name, field):
        """Add a ``field`` with the given ``name`` to an MmStats instance

        Raises ``OutOfSpaceError`` exception if you attempt to add a field and
        there's no space left in the mmap. Set a large extra_space kwarg to
        fix.
        """
        if hasattr(self, name):
            raise NameCollisionError(
                    "Instance already has attribute named `%s`" % name)
        size = self._add_field(name, field)
        if self._offset + size > self.size:
            raise OutOfSpaceError(
                    "Cannot create field `%s` - requires %d bytes but only %d "
                    "free. Raise extra_space from %d to at least %d" % (
                        name, size, self.size - self._offset, self.extra_space,
                        self.extra_space + size)
                )
        # _add_field(...) populated self._fields[name] with a state instance
        self._init_field(self._fields[name])

        # Add the field as an attribute to the class to support descriptors
        setattr(self.__class__, name, field)

    def _add_field(self, name, field):
        """Given a name and Field instance, add this field and return size"""
        # Stats need a place to store their per Mmstats instance state
        state = self._fields[name] = FieldState(field)

        # Call field._new to determine size
        return field._new(state, self.label_prefix, name)

    def _init_field(self, state):
        """Given a field's ``state`` object,  call it's _init(...) method"""
        self._offset = state.field._init(state, self._mm_ptr, self._offset)

    def _init_fields(self):
        """Once all fields have been added, initialize them in mmap"""
        map(self._init_field, self._fields.values())

    @property
    def filename(self):
        return self._filename

    @property
    def label_prefix(self):
        return self._label_prefix

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
