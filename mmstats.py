import ctypes
import mmap
import os
import tempfile
import threading


BUFFER_IDX_TYPE = ctypes.c_byte
LABEL_SZ_TYPE = ctypes.c_ushort


def _init_mmap(path=None, filename=None, size=None):
    """Create mmap instance"""
    if path is None:
        path = tempfile.gettempdir()

    if filename is None:
        filename = 'mmstats-%d' % os.getpid()
        t = threading.current_thread()
        if t.ident:
            filename += '-%d' % t.ident

    full_path = os.path.join(path, filename)

    # Create new empty file to back memory map on disk
    fd = os.open(full_path, os.O_CREAT | os.O_TRUNC | os.O_RDWR)

    # Zero out the file to insure it's the right size
    os.write(fd, '\x00' * mmap.PAGESIZE)

    return mmap.mmap(fd, mmap.PAGESIZE, mmap.MAP_SHARED, mmap.PROT_WRITE)


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
    """Base class for all stats"""

    def __init__(self, label=None):
        self._struct = None # initialized in _init
        if label:
            self.label = label
        else:
            self.label = None

    def _init(self, parent_fields, label_prefix, attrname, mm, offset):
        """Initializes mmaped buffers and returns next offset"""
        self.key = attrname
        if self.label is None:
            self.label = label_prefix + attrname
        else:
            self.label = label_prefix + self.label

        # Use state on parent to store per-instance-per-field state
        parent_fields[self.key] = FieldState()
        state = parent_fields[self.key]
        return self._init_struct(state, mm, offset)

    def _init_struct(self, state, mm, offset):
        """Initializes mmaped buffers and returns next offset"""
        # We don't need a reference to the Struct Class anymore, but there's no
        # reason to throw it away
        state._StructCls = _create_struct(self.label, self.buffer_type)
        state._struct = state._StructCls.from_buffer(mm, offset)
        state._struct.label_sz = len(self.label)
        state._struct.label = self.label
        state._struct.type_signature = self.type_signature
        state._struct.write_buffer = 0
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
        state._StructCls = _create_struct(self.label, self.buffer_type,
                buffers=2)
        state._struct = state._StructCls.from_buffer(mm, offset)
        state._struct.label_sz = len(self.label)
        state._struct.label = self.label
        state._struct.type_signature = self.type_signature
        state._struct.write_buffer = 0
        state._struct.buffers = 0, 0
        return offset + ctypes.sizeof(state._StructCls)

    def __get__(self, inst, owner):
        state = inst._fields[self.key]
        # Get from the read buffer
        ret = state._struct.buffers[state._struct.write_buffer ^ 1]
        return ret

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
    signature_type = 'L'


class IntStat(DoubleBufferedStat):
    """32bit Double Buffered Signed Integer field"""
    buffer_type = ctypes.c_int32
    signature_type = 'l'


class ShortStat(DoubleBufferedStat):
    """16bit Double Buffered Signed Integer field"""
    buffer_type = ctypes.c_int16


class UShortStat(DoubleBufferedStat):
    """16bit Double Buffered Unsigned Integer field"""
    buffer_type = ctypes.c_uint16


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
