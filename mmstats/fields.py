import array
import ctypes
import math
import time

from . import defaults


class DuplicateFieldName(Exception):
    """Cannot add 2 fields with the same name to MmStat instances"""


def _create_struct(label, type_, type_signature, buffers=None):
    """Helper to wrap dynamic Structure subclass creation"""
    if isinstance(label, unicode):
        label = label.encode('utf8')

    fields = [
        ('label_sz', defaults.SIZE_TYPE),
        ('label', ctypes.c_char * len(label)),
        ('type_sig_sz', defaults.SIZE_TYPE),
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
        state._struct.write_buffer = defaults.WRITE_BUFFER_UNUSED
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


class _MovingAverageInternal(_InternalFieldInterface):
    def __init__(self, state):
        _InternalFieldInterface.__init__(self, state)

        self._max = state.field.size
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


class MovingAverageField(ComplexDoubleBufferedField):
    buffer_type = ctypes.c_double
    InternalClass = _MovingAverageInternal

    def __init__(self, size=100, **kwargs):
        super(MovingAverageField, self).__init__(**kwargs)
        self.size = size


class _TimerContext(object):
    """Class to wrap timer state"""
    def __init__(self, timer=time.time):
        self._timer = timer
        self.start = timer()
        self.end = None

    def get_time(self):
        return self._timer()

    @property
    def done(self):
        """True if timer context has stopped"""
        return self.end is not None

    @property
    def elapsed(self):
        """Returns time elapsed in context"""
        if self.done:
            return self.end - self.start
        else:
            return self.get_time() - self.start

    def stop(self):
        self.end = self.get_time()


class TimerField(MovingAverageField):
    """Moving average field that provides a context manager for easy timings

    As a context manager:
    >>> class T(MmStats):
    ...     timer = TimerField()
    >>> t = T()
    >>> with t.timer as ctx:
    ...     assert ctx.elapsed > 0.0
    >>> assert t.timer.value > 0.0
    >>> assert t.timer.last > 0.0
    """
    def __init__(self, timer=time.time, **kwargs):
        super(TimerField, self).__init__(**kwargs)
        self.timer = timer

    class InternalClass(_MovingAverageInternal):
        def __init__(self, state):
            _MovingAverageInternal.__init__(self, state)
            self._ctx = None
            self.timer = state.field.timer

        def start(self):
            """Start the timer"""
            self._ctx = _TimerContext(self.timer)

        def stop(self):
            """Stop the timer"""
            self._ctx.stop()
            self.add(self._ctx.elapsed)

        def __enter__(self):
            self.start()
            return self._ctx

        def __exit__(self, exc_type, exc_value, exc_tb):
            self.stop()

        @property
        def last(self):
            """Get the last recorded value"""
            if self._ctx is None:
                return 0.0
            else:
                return self._ctx.elapsed


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

    def __init__(self, size=defaults.DEFAULT_STRING_SIZE, **kwargs):
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
