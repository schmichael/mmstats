import ctypes
import mmap
import os
import tempfile

import libgettid


PAGESIZE = mmap.PAGESIZE
BUFFER_IDX_TYPE = ctypes.c_byte
LABEL_SZ_TYPE = ctypes.c_ushort
WRITE_BUFFER_UNUSED = 255


def _init_mmap(path=None, filename=None, size=PAGESIZE):
    """Given path, filename, or size => filename, size, mmap"""
    if path is None:
        path = tempfile.gettempdir()

    if filename is None:
        filename = 'mmstats-%d' % os.getpid()
        tid = libgettid.gettid()
        if tid:
            filename += '-%d' % tid

    full_path = os.path.join(path, filename)

    # Create new empty file to back memory map on disk
    fd = os.open(full_path, os.O_CREAT | os.O_TRUNC | os.O_RDWR)

    # Round size up to nearest PAGESIZE
    if size % PAGESIZE:
        size = size + (PAGESIZE - (size % PAGESIZE))

    # Zero out the file to insure it's the right size
    for _ in range(0, size, PAGESIZE):
        os.write(fd, '\x00' * PAGESIZE)

    m =  mmap.mmap(fd, size, mmap.MAP_SHARED, mmap.PROT_WRITE)
    return (filename, size, m)


def _create_struct(label, type_, buffers=1):
    """Helper to wrap dynamic Structure subclass creation"""
    if isinstance(label, unicode):
        label = label.encode('utf8')

    fields = [
        ('label_sz', LABEL_SZ_TYPE),
        ('label', ctypes.c_char * len(label)),
        ('type_signature', ctypes.c_char),
        ('write_buffer', ctypes.c_ubyte),
    ]

    if buffers == 1:
        fields.append(('value', type_))
    else:
        fields.append(('buffers', (type_ * buffers)))

    return type("%sStruct" % label.title(),
                (ctypes.Structure,),
                {'_fields_': fields, '_pack_': 1}
            )


class Stat(object):
    def __init__(self, label=None):
        self._struct = None # initialized in _init
        if label:
            self.label = label
        else:
            self.label = None

    def _init(self, parent_fields, label_prefix, attrname, mm, offset):
        """Initializes mmaped buffers and returns next offset"""
        # Key is used to reference field state on the parent instance
        self.key = attrname

        # Use state on parent to store per-instance-per-field state
        parent_fields[self.key] = FieldState()
        state = parent_fields[self.key]

        # Label defaults to attribute name if no label specified
        if self.label is None:
            state.label = label_prefix + attrname
        else:
            state.label = label_prefix + self.label
        return self._init_struct(state, mm, offset)

    def _init_struct(self, state, mm, offset):
        """Initializes mmaped buffers and returns next offset"""
        # We don't need a reference to the Struct Class anymore, but there's no
        # reason to throw it away
        state._StructCls = _create_struct(state.label, self.buffer_type)
        state._struct = state._StructCls.from_buffer(mm, offset)
        state._struct.label_sz = len(state.label)
        state._struct.label = state.label
        state._struct.type_signature = self.type_signature
        state._struct.write_buffer = WRITE_BUFFER_UNUSED
        state._struct.value = 0
        return offset + ctypes.sizeof(state._StructCls)

    def __get__(self, inst, owner):
        return inst._fields[self.key]._struct.value

    def __set__(self, inst, value):
        inst._fields[self.key]._struct.value = value

    @property
    def type_signature(self):
        return self.buffer_type._type_

    def __repr__(self):
        return '%s(label=%r)' % (self.__class__.__name__, self.label)


class DoubleBufferedStat(Stat):
    def _init_struct(self, state, mm, offset):
        state._StructCls = _create_struct(state.label, self.buffer_type,
                buffers=2)
        state._struct = state._StructCls.from_buffer(mm, offset)
        state._struct.label_sz = len(state.label)
        state._struct.label = state.label
        state._struct.type_signature = self.type_signature
        state._struct.write_buffer = 0
        state._struct.buffers = 0, 0
        return offset + ctypes.sizeof(state._StructCls)

    def __get__(self, inst, owner):
        state = inst._fields[self.key]
        # Get from the read buffer
        return state._struct.buffers[state._struct.write_buffer ^ 1]

    def __set__(self, inst, value):
        state = inst._fields[self.key]
        # Set the write buffer
        state._struct.buffers[state._struct.write_buffer] = value
        # Swap the write buffer
        state._struct.write_buffer ^= 1


class FieldState(object):
    """Holds field state for each stat instance"""


class UIntStat(DoubleBufferedStat):
    """32bit Double Buffered Unsigned Integer field"""
    buffer_type = ctypes.c_uint32
    type_signature = 'I'


class IntStat(DoubleBufferedStat):
    """32bit Double Buffered Signed Integer field"""
    buffer_type = ctypes.c_int32
    type_signature = 'i'


class ShortStat(DoubleBufferedStat):
    """16bit Double Buffered Signed Integer field"""
    buffer_type = ctypes.c_int16


class UShortStat(DoubleBufferedStat):
    """16bit Double Buffered Unsigned Integer field"""
    buffer_type = ctypes.c_uint16


class ByteStat(Stat):
    """8bit Signed Integer Field"""
    buffer_type = ctypes.c_byte


class BoolStat(Stat):
    """Boolean Field"""
    # Avoid potential ambiguity and marshal bools to 0/1 manually
    buffer_type = ctypes.c_byte
    type_signature = '?'

    def __get__(self, inst, owner):
        return inst._fields[self.key]._struct.value == 1

    def __set__(self, inst, value):
        inst._fields[self.key]._struct.value = 1 if value else 0


class MmStats(object):
    """Stats models should inherit from this"""

    def __init__(self, filename=None, label_prefix=None):
        if label_prefix is None:
            label_prefix = ''
        self._mmap = _init_mmap(filename=filename)

        self._mmap[0] = '\x01' # Stupid version number
        offset = 1

        # Store state for this instance's fields
        fields = {}
        for attrname, attrval in self.__class__.__dict__.items():
            if isinstance(attrval, Stat):
                offset = attrval._init(
                        fields, label_prefix, attrname, self._mmap, offset)

        self._fields = fields
        self._offset = offset
