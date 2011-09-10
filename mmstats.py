import ctypes
import mmap
import os
import tempfile

import libgettid


PAGESIZE = mmap.PAGESIZE
BUFFER_IDX_TYPE = ctypes.c_byte
LABEL_SZ_TYPE = ctypes.c_ushort
WRITE_BUFFER_UNUSED = 255
DEFAULT_PATH = os.environ.get('MMSTATS_PATH', tempfile.gettempdir())


class DuplicateStatName(Exception):
    """Cannot add 2 stats with the same name to MmStat instances"""


def _init_mmap(path=None, filename=None):
    """Given path, filename => filename, size, mmap"""
    if path is None:
        path = DEFAULT_PATH

    if filename is None:
        filename = 'mmstats-%d' % os.getpid()
        tid = libgettid.gettid()
        if tid:
            filename += '-%d' % tid

    full_path = os.path.join(path, filename)

    # Create new empty file to back memory map on disk
    fd = os.open(full_path, os.O_CREAT | os.O_TRUNC | os.O_RDWR)

    # Zero out the file
    os.write(fd, '\x00' * PAGESIZE)

    m = mmap.mmap(fd, PAGESIZE, mmap.MAP_SHARED, mmap.PROT_WRITE)
    return (full_path, PAGESIZE, m)


def _create_struct(label, type_, buffers=None):
    """Helper to wrap dynamic Structure subclass creation"""
    if isinstance(label, unicode):
        label = label.encode('utf8')

    fields = [
        ('label_sz', LABEL_SZ_TYPE),
        ('label', ctypes.c_char * len(label)),
        ('type_signature', ctypes.c_char),
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


class Stat(object):
    def __init__(self, label=None):
        self._struct = None # initialized in _init
        if label:
            self.label = label
        else:
            self.label = None

    def _new(self, state, label_prefix, attrname, buffers=None):
        """Creates new data structure for stat in state instance"""
        # Key is used to reference field state on the parent instance
        self.key = attrname

        # Label defaults to attribute name if no label specified
        if self.label is None:
            state.label = label_prefix + attrname
        else:
            state.label = label_prefix + self.label
        state._StructCls = _create_struct(
                state.label, self.buffer_type, buffers)
        state.size = ctypes.sizeof(state._StructCls)
        return state.size

    def _init(self, state, mm, offset):
        """Initializes value of stat's data structure"""
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
    def _new(self, state, label_prefix, attrname):
        return super(DoubleBufferedStat, self)._new(
                state, label_prefix, attrname, buffers=2)

    def _init(self, state, mm, offset):
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

    def __init__(self, stat):
        self.stat = stat


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
        # Setup label prefix
        self._label_prefix = '' if label_prefix is None else label_prefix

        self._filename, self._size, self._mmap = _init_mmap(filename=filename)

        self._mmap[0] = '\x01' # Stupid version number
        self._offset = 1

        # Store state for this instance's fields
        self._fields = {}

        total_size = self._offset
        for attrname, attrval in self.__class__.__dict__.items():
            if isinstance(attrval, Stat):
                total_size += self._add_stat(attrname, attrval)

        # Finally initialize thes stats
        self._init_stats(total_size)

    @classmethod
    def add_stat(cls, name, stat):
        """Given a name and Stat instance, add field to this mmstat class"""
        if name in cls.__dict__:
            raise DuplicateStatName(name)
        else:
            setattr(cls, name, stat)

    def _add_stat(self, name, stat):
        """Given a name and Stat instance, add this field and retun size"""
        # Stats need a place to store their per Mmstats instance state 
        state = self._fields[name] = FieldState(stat)

        # Call stat._new to determine size
        return stat._new(state, self.label_prefix, name)

    def _init_stats(self, total_size):
        """Once all stats have been added, initialize them in mmap"""
        # Resize mmap (can only be done *before* stats are initialized
        if total_size > self.size:
            if total_size % PAGESIZE:
                self._mmap.resize(
                        total_size + (PAGESIZE - (total_size % PAGESIZE))
                    )
            else:
                self._mmap.resize(total_size)

        for state in self._fields.values():
            # 2nd Call stat._init to initialize new stat
            self._offset = state.stat._init(state, self._mmap, self._offset)

    @property
    def filename(self):
        return self._filename

    @property
    def label_prefix(self):
        return self._label_prefix

    @property
    def size(self):
        return self._mmap.size()
