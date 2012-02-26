import array
import ctypes
import math
import mmap
import os
import sys
import tempfile
import time

from mmstats import libgettid, _mmap


PAGESIZE = mmap.PAGESIZE
BUFFER_IDX_TYPE = ctypes.c_byte
SIZE_TYPE = ctypes.c_ushort
WRITE_BUFFER_UNUSED = 255
DEFAULT_PATH = os.environ.get('MMSTATS_PATH', tempfile.gettempdir())
DEFAULT_FILENAME = os.environ.get('MMSTATS_FILES', 'mmstats-%PID%-%TID%')
DEFAULT_STRING_SIZE = 255


class DuplicateFieldName(Exception):
    """Cannot add 2 fields with the same name to MmStat instances"""


def _init_mmap(path=DEFAULT_PATH, filename=DEFAULT_FILENAME, size=PAGESIZE):
    """Given path, filename => filename, size, mmap

    In `filename` "%PID%" and "%TID%" will be replaced with pid and thread id
    """
    # Replace %PID% with actual pid
    filename = filename.replace('%PID%', str(os.getpid()))
    # Replace %TID% with thread id or 0 if thread id is None
    filename = filename.replace('%TID%', str(libgettid.gettid() or 0))

    full_path = os.path.join(path, filename)

    # Create new empty file to back memory map on disk
    fd = os.open(full_path, os.O_CREAT | os.O_TRUNC | os.O_RDWR)
    if size > PAGESIZE:
        if size % PAGESIZE:
            size = size + (PAGESIZE - (size % PAGESIZE))
    else:
        size = PAGESIZE

    # Zero out the file
    os.ftruncate(fd, size)
    m_ptr = _mmap.mmap(size, fd)
    return (fd, full_path, size, m_ptr)


def _create_struct(label, type_, type_signature, buffers=None):
    """Helper to wrap dynamic Structure subclass creation"""
    if isinstance(label, unicode):
        label = label.encode('utf8')

    fields = [
        ('label_sz', SIZE_TYPE),
        ('label', ctypes.c_char * len(label)),
        ('type_sig_sz', SIZE_TYPE),
        ('type_signature', ctypes.c_char * len(type_signature)),
        ('write_buffer', ctypes.c_ubyte),
    ]

    if buffers is None:
        fields.append(('value', type_))
    else:
        fields.append(('buffers', (type_ * buffers)))

    return type("%sStruct" % label.title(),
                (ctypes.Structure,),
                {'_fields_': fields, '_pack_': 1}
            )


class Field(object):
    initial = 0

    def __init__(self, label=None):
        self._struct = None  # initialized in _init
        if label:
            self.label = label
        else:
            self.label = None

    def _new(self, state, label_prefix, attrname, buffers=None):
        """Creates new data structure for field in state instance"""
        # Key is used to reference field state on the parent instance
        self.key = attrname

        # Label defaults to attribute name if no label specified
        if self.label is None:
            state.label = label_prefix + attrname
        else:
            state.label = label_prefix + self.label
        state._StructCls = _create_struct(
                state.label, self.buffer_type,
                self.type_signature, buffers)
        state.size = ctypes.sizeof(state._StructCls)
        return state.size

    def _init(self, state, mm_ptr, offset):
        """Initializes value of field's data structure"""
        state._struct = state._StructCls.from_address(mm_ptr + offset)
        state._struct.label_sz = len(state.label)
        state._struct.label = state.label
        state._struct.type_sig_sz = len(self.type_signature)
        state._struct.type_signature = self.type_signature
        state._struct.write_buffer = WRITE_BUFFER_UNUSED
        state._struct.value = self.initial
        return offset + ctypes.sizeof(state._StructCls)

    @property
    def type_signature(self):
        return self.buffer_type._type_

    def __repr__(self):
        return '%s(label=%r)' % (self.__class__.__name__, self.label)


class NonDataDescriptorMixin(object):
    """Mixin to add single buffered __get__ method"""

    def __get__(self, inst, owner):
        if inst is None:
            return self
        return inst._fields[self.key]._struct.value


class DataDescriptorMixin(object):
    """Mixin to add single buffered __set__ method"""

    def __set__(self, inst, value):
        inst._fields[self.key]._struct.value = value


class BufferedDescriptorMixin(object):
    """\
    Mixin to add double buffered descriptor methods

    Always read/write as double buffering doesn't make sense for readonly
    fields
    """

    def __get__(self, inst, owner):
        if inst is None:
            return self
        state = inst._fields[self.key]
        # Get from the read buffer
        return state._struct.buffers[state._struct.write_buffer ^ 1]

    def __set__(self, inst, value):
        state = inst._fields[self.key]
        # Set the write buffer
        state._struct.buffers[state._struct.write_buffer] = value
        # Swap the write buffer
        state._struct.write_buffer ^= 1


class ReadOnlyField(Field, NonDataDescriptorMixin):
    def __init__(self, label=None, value=None):
        super(ReadOnlyField, self).__init__(label=label)
        self.value = value

    def _init(self, state, mm, offset):
        if self.value is None:
            # Value can't be None
            raise ValueError("value must be set")
        elif callable(self.value):
            # If value is a callable, resolve it now during initialization
            self.value = self.value()

        # Call super to do standard initialization
        new_offset = super(ReadOnlyField, self)._init(state, mm, offset)
        # Set the static field now
        state._struct.value = self.value

        # And return the offset as usual
        return new_offset


class ReadWriteField(Field, NonDataDescriptorMixin, DataDescriptorMixin):
    """Base class for simple writable fields"""


class DoubleBufferedField(Field):
    """Base class for double buffered writable fields"""
    def _new(self, state, label_prefix, attrname):
        return super(DoubleBufferedField, self)._new(
                state, label_prefix, attrname, buffers=2)

    def _init(self, state, mm_ptr, offset):
        state._struct = state._StructCls.from_address(mm_ptr + offset)
        state._struct.label_sz = len(state.label)
        state._struct.label = state.label
        state._struct.type_sig_sz = len(self.type_signature)
        state._struct.type_signature = self.type_signature
        state._struct.write_buffer = 0
        state._struct.buffers = 0, 0
        return offset + ctypes.sizeof(state._StructCls)


class ComplexDoubleBufferedField(DoubleBufferedField):
    """Base Class for fields with complex internal state like Counters

    Set InternalClass in your subclass
    """
    InternalClass = None

    def _init(self, state, mm_ptr, offset):
        offset = super(ComplexDoubleBufferedField, self)._init(
                state, mm_ptr, offset)
        self._init_internal(state)
        return offset

    def _init_internal(self, state):
        if self.InternalClass is None:
            raise NotImplementedError(
                    "Must set %s.InternalClass" % type(self).__name__)
        state.internal = self.InternalClass(state)

    def __get__(self, inst, owner):
        if inst is None:
            return self
        return inst._fields[self.key].internal


class _InternalFieldInterface(object):
    """Base class used by internal field interfaces like counter"""
    def __init__(self, state):
        self._struct = state._struct

    @property
    def value(self):
        return self._struct.buffers[self._struct.write_buffer ^ 1]

    @value.setter
    def value(self, v):
        self._set(v)

    def _set(self, v):
        # Set the write buffer
        self._struct.buffers[self._struct.write_buffer] = v
        # Swap the write buffer
        self._struct.write_buffer ^= 1


class CounterField(ComplexDoubleBufferedField):
    """Counter field supporting an inc() method and value attribute"""
    buffer_type = ctypes.c_uint64
    type_signature = 'Q'

    class InternalClass(_InternalFieldInterface):
        """Internal counter class used by CounterFields"""
        def inc(self, n=1):
            self._set(self.value + n)


class AverageField(ComplexDoubleBufferedField):
    """Average field supporting an add() method and value attribute"""
    buffer_type = ctypes.c_double

    class InternalClass(_InternalFieldInterface):
        """Internal mean class used by AverageFields"""

        def __init__(self, state):
            _InternalFieldInterface.__init__(self, state)

            # To recalculate the mean we need to store the overall count
            self._count = 0
            # Keep the overall total internally
            self._total = 0.0

        def add(self, value):
            """Add a new value to the average"""
            self._count += 1
            self._total += value
            self._set(self._total / self._count)


class MovingAverageField(ComplexDoubleBufferedField):
    buffer_type = ctypes.c_double

    def __init__(self, window_size=100, **kwargs):
        super(MovingAverageField, self).__init__(**kwargs)
        self.window_size = window_size

    class InternalClass(_InternalFieldInterface):
        def __init__(self, state):
            _InternalFieldInterface.__init__(self, state)

            self._max = state.field.window_size
            self._window = array.array('d', [0.0] * self._max)
            self._idx = 0
            self._full = False

        def add(self, value):
            """Add a new value to the moving average"""
            self._window[self._idx] = value
            if self._full:
                self._set(math.fsum(self._window) / self._max)
            else:
                # Window isn't full, divide by current index
                self._set(math.fsum(self._window) / (self._idx + 1))

            if self._idx == (self._max - 1):
                # Reset idx
                self._idx = 0
                self._full = True
            else:
                self._idx += 1


class BufferedDescriptorField(DoubleBufferedField, BufferedDescriptorMixin):
    """Base class for double buffered descriptor fields"""


class UInt64Field(BufferedDescriptorField):
    """Unbuffered read-only 64bit Unsigned Integer field"""
    buffer_type = ctypes.c_uint64
    type_signature = 'Q'


class UIntField(BufferedDescriptorField):
    """32bit Double Buffered Unsigned Integer field"""
    buffer_type = ctypes.c_uint32
    type_signature = 'I'


class IntField(BufferedDescriptorField):
    """32bit Double Buffered Signed Integer field"""
    buffer_type = ctypes.c_int32
    type_signature = 'i'


class ShortField(BufferedDescriptorField):
    """16bit Double Buffered Signed Integer field"""
    buffer_type = ctypes.c_int16


class UShortField(BufferedDescriptorField):
    """16bit Double Buffered Unsigned Integer field"""
    buffer_type = ctypes.c_uint16


class ByteField(ReadWriteField):
    """8bit Signed Integer Field"""
    buffer_type = ctypes.c_byte


class FloatField(BufferedDescriptorField):
    """32bit Float Field"""
    buffer_type = ctypes.c_float


class StaticFloatField(ReadOnlyField):
    """Unbuffered read-only 32bit Float field"""
    buffer_type = ctypes.c_float


class DoubleField(BufferedDescriptorField):
    """64bit Double Precision Float Field"""
    buffer_type = ctypes.c_double


class StaticDoubleField(ReadOnlyField):
    """Unbuffered read-only 64bit Float field"""
    buffer_type = ctypes.c_double


class BoolField(ReadWriteField):
    """Boolean Field"""
    # Avoid potential ambiguity and marshal bools to 0/1 manually
    buffer_type = ctypes.c_byte
    type_signature = '?'

    def __init__(self, initial=False, **kwargs):
        self.initial = initial
        super(BoolField, self).__init__(**kwargs)

    def __get__(self, inst, owner):
        if inst is None:
            return self
        return inst._fields[self.key]._struct.value == 1

    def __set__(self, inst, value):
        inst._fields[self.key]._struct.value = 1 if value else 0


class StringField(ReadWriteField):
    """UTF-8 String Field"""
    initial = ''

    def __init__(self, size=DEFAULT_STRING_SIZE, **kwargs):
        self.size = size
        self.buffer_type = ctypes.c_char * size
        super(StringField, self).__init__(**kwargs)

    @property
    def type_signature(self):
        return '%ds' % self.size

    def __get__(self, inst, owner):
        if inst is None:
            return self
        return inst._fields[self.key]._struct.value.decode('utf8')

    def __set__(self, inst, value):
        if isinstance(value, unicode):
            value = value.encode('utf8')
            if len(value) > self.size:
                # Round trip utf8 trimmed strings to make sure it's stores
                # valid utf8 bytes
                value = value[:self.size]
                value = value.decode('utf8', 'ignore').encode('utf8')
        elif len(value) > self.size:
            value = value[:self.size]
        inst._fields[self.key]._struct.value = value


class StaticUIntField(ReadOnlyField):
    """Unbuffered read-only 32bit Unsigned Integer field"""
    buffer_type = ctypes.c_uint32
    type_signature = 'I'


class StaticInt64Field(ReadOnlyField):
    """Unbuffered read-only 64bit Signed Integer field"""
    buffer_type = ctypes.c_int64
    type_signature = 'q'


class StaticUInt64Field(ReadOnlyField):
    """Unbuffered read-only 64bit Unsigned Integer field"""
    buffer_type = ctypes.c_uint64
    type_signature = 'Q'


class StaticTextField(ReadOnlyField):
    """Unbuffered read-only UTF-8 encoded String field"""
    initial = ''
    buffer_type = ctypes.c_char * 256
    type_signature = '256s'


class StaticListField(ReadOnlyField):
    """Unbuffered read-only List field"""
    #TODO


class StaticMappingField(ReadOnlyField):
    """Unbuffered read-only List field"""
    #TODO


class FieldState(object):
    """Holds field state for each Field instance"""

    def __init__(self, field):
        self.field = field


class BaseMmStats(object):
    """Stats models should inherit from this"""

    def __init__(self, path=DEFAULT_PATH, filename=DEFAULT_FILENAME,
            label_prefix=None):
        """\
        Optionally given a filename or label_prefix, create an MmStats instance
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
                if attrname not in self._fields and isinstance(attrval, Field):
                    total_size += self._add_field(attrname, attrval)

        self._fd, self._filename, self._size, self._mm_ptr = _init_mmap(
            path=path, filename=filename, size=total_size)
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
    pid = StaticUIntField(label="sys.pid", value=os.getpid)
    tid = StaticInt64Field(label="sys.tid", value=libgettid.gettid)
    uid = StaticUInt64Field(label="sys.uid", value=os.getuid)
    gid = StaticUInt64Field(label="sys.gid", value=os.getgid)
    python_version = StaticTextField(label="org.python.version",
            value=lambda: sys.version.replace("\n", ""))
    created = StaticDoubleField(label="sys.created", value=time.time)
    #TODO Add sys.path? might be a little overboard
    """
    python_path = StaticTextField(
            label="org.python.path",
            item_type=str,
            value=sys.path
        )
    """
