from abc import ABC, abstractmethod
from collections.abc import MutableMapping, MutableSequence, Sequence
from .compression import compress, decompress
import functools
import operator
import re
import struct
import util

#-------------------------------------- Abstract Base Classes --------------------------------------

class TAG_Abstract(ABC):
    """Abstract Base Class of all tag types"""
    
    ID = NotImplemented
    """TAG_ID of this Tag"""

    @classmethod
    @abstractmethod
    def from_bytes(cls, iterable):
        """Create a tag from an iterable of NBT data bytes"""
        pass
    
    @classmethod
    def from_snbt(cls, snbt):
        """Create a tag from a SNBT formatted string"""
        if not re.compile(cls.regex).fullmatch(snbt):
            raise ValueError(f'Invalid SNBT \'{snbt}\' for {cls}')

    @abstractmethod
    def to_bytes(self):
        """Return NBT data bytearray from self"""
        pass

    @abstractmethod
    def to_snbt(self):
        """Return a SNBT representation of this tag"""
        pass

    @abstractmethod
    def valueType(value):
        """Convert value to the same type as this tag's .value"""
        pass

    def __eq__(self, other):
        return self.value.__eq__(self.valueType(other))
    
    def __ge__(self, other):
        return self.value.__ge__(self.valueType(other))
    
    def __gt__(self, other):
        return self.value.__gt__(self.valueType(other))
    
    def __le__(self, other):
        return self.value.__le__(self.valueType(other))
    
    def __lt__(self, other):
        return self.value.__lt__(self.valueType(other))
    
    def __repr__(self):
        return self.to_snbt()

class TAG_Value(TAG_Abstract):
    """Abstract Base Class for all simple value tag types"""

    def __init__(self, value = None):
        value = 0 if value is None else value
        self.value = value

    def bit_length(self):
        """Returns the BIT length of this tag's value after encoding"""
        return len(self._value) * 8

    def to_bytes(self):
        return self._value
    
util.make_wrappers(TAG_Value, coercedMethods = ['__add__', '__mod__', '__rmod__', '__mul__', '__rmul__'])

class TAG_Number(TAG_Value):
    """Abstract Base Class for numerical tag types

    Assignments to .value are automatically encoded and boundary checked
    """

    fmt = NotImplemented
    """Struct format string for packing and unpacking"""
    
    regex = NotImplemented
    """Regular Expression used for SNBT matching
    Use with re.Pattern.fullmatch(regex) !
    """
    
    suffix = NotImplemented
    """SNBT value suffix"""
    
    @classmethod
    def from_bytes(cls, iterable):
        byteValue = util.read_bytes(iterable, n = len(cls()))
        return cls( struct.unpack(cls.fmt, byteValue)[0] )
    
    def to_snbt(self):
        return f'{self.value}{self.suffixes[0]}'

    @property
    def value(self):
        return struct.unpack(self.fmt, self._value)[0]

    @value.setter
    def value(self, newValue):
        self._value = struct.pack(self.fmt, self.valueType(newValue))

    def __len__(self):
        """Returns the BYTE length of this tag's value after encoding"""
        return len(self._value)
    
util.make_wrappers( TAG_Number, 
    coercedMethods = [
        'conjugate',
        'imag',
        'real',
        '__abs__',
        '__ceil__',
        '__floor__',
        '__floordiv__',
        '__neg__',
        '__pos__',
        '__pow__',
        '__round__',
        '__sub__',
        '__truediv__',
        '__trunc__'
    ],
    nonCoercedMethods = [
        'as_integer_ratio',
        '__bool__',
        '__divmod__',
        '__float__',
        '__int__',
        '__radd__',
        '__rdivmod__',
        '__rfloordiv__',
        '__rpow__',
        '__rsub__',
        '__rtruediv__',
        '__str__'
    ]
)

class TAG_Integer(TAG_Number):
    """Abstract Base Class for integer numerical tag types"""
    
    valueType = int
    
    @property
    def unsigned(self):
        """The unsigned equivalent of this tag's value"""
        return struct.unpack(self.fmt.upper(), self._value)[0]
    
    @unsigned.setter
    def unsigned(self):
        self._value = struct.pack(self.fmt.upper(), self.valueType(newValue))

util.make_wrappers( TAG_Integer,
    coercedMethods = [
        'denominator',
        'numerator',
        '__and__',
        '__invert__',
        '__lshift__',
        '__or__',
        '__rshift__',
        '__xor__'
    ],
    nonCoercedMethods = [
        '__rand__',
        '__index__',
        '__rlshift__',
        '__ror__',
        '__rrshift__',
        '__rxor__'
    ]
)

class TAG_Decimal(TAG_Number):
    """Abstract Base Class for decimal numerical tag types"""
    
    valueType = float
    
    @classmethod
    def fromhex(cls, string):
        return cls( float.fromhex(string) )

util.make_wrappers(TAG_Decimal, nonCoercedMethods=['hex','is_integer'])

class TAG_Sequence(TAG_Abstract, Sequence):
    """Abstract Base Class for sequence tag types"""
    pass

util.make_wrappers(TAG_Sequence, nonCoercedMethods = ['__getitem__', '__iter__', '__len__'])

class TAG_MutableSequence(TAG_Sequence, MutableSequence):
    """Abstract Base Class for Mutable Sequence tag types"""
    
    valueType = list
    
    def __init__(self, value = None):
        """Checks that all elements are type compatible through self.append"""
        value = [] if value is None else value
        self.value = []
        
        for i in value:
            self.append(i)

    def append(self, value):
        self.value.append(self.elementType(value))

    @staticmethod
    def decode_bytes(iterable, elementType):
        """Convert bytes -> sequence of values of elementType"""
        iterator = iter(iterable)
        length = TAG_Int.from_bytes(iterator)
        
        return [elementType.from_bytes(iterator) for _ in range(length)]
    
    @staticmethod
    def decode_snbt(snbt, elementType):
        """Convert snbt -> Sequence of values of elementType"""
        return [elementType(i) for i in snbt.strip('[]').split(',')]

    @property
    def elementID(self):
        return self.elementType.ID

    def insert(self, key, value):
        self.value = self[:key] + [value] + self[key:]
    
    def sort(self, *, key=None, reverse=False):
        self.value.sort(key=key, reverse=reverse)
    
    def to_bytes(self):
        encoded = TAG_Int(len(self)).to_bytes()
        
        for element in self:
            encoded += element.to_bytes()
            if isinstance(element, TAG_Compound):
                encoded += TAG_End().to_bytes()
    
        return encoded
    
    def to_snbt(self):
        return f'[{self.prefix}{",".join( [repr(i) for i in self.value] )}]'
    
    def __add__(self, other):
        return type(self)( self.value + [self.elementType(i) for i in other] )

    def __delitem__(self, key):
        del self.value[key]


    def __setitem__(self, key, value):
        """Replace self[key] with value.
        
        Value must be able to convert to self.elementType
        """
        self.value[key] = self.elementType(value)

util.make_wrappers( TAG_MutableSequence,
    coercedMethods = [
        'copy',
        '__mul__', 
        '__rmul__'
    ],
    nonCoercedMethods = [
        '__radd__'
    ]
)

class TAG_Array(TAG_MutableSequence):
    """Abstract Base Class for Array tag types"""
    
    prefix = NotImplemented
    """SNBT list Prefix"""
    
    @classmethod
    def from_bytes(cls, iterable):
        return cls( super().decode_bytes(iterable, cls.elementType) )
    
    @classmethod
    def from_snbt(cls, snbt : str):
        snbt = snbt.lower()
        prefix = cls.prefix.lower()
        try:
            assert snbt.find(prefix) != -1
            assert snbt[0] == '[' and snbt[-1] == ']'
        except:
            raise ValueError(f'Invalid SNBT \'{snbt}\' for {cls}')
            
        return cls( super().decode_snbt(snbt, cls.elementType) )
    
    @classmethod
    @property
    def regex(cls):
        prefix = cls.prefix
        elem = cls.elementType.regex
        return f'(\\[{prefix}({elem},)*(?(2)({elem})|({elem})?)\\])'

#---------------------------------------- Concrete Classes -----------------------------------------

class TAG():
    """Class storing static methods
    To be used when the correct tag type is indeterminate before runtime
    """
    
    @staticmethod
    def from_snbt(snbt):
    
        if re.compile(r'[\d]').fullmatch(snbt) is not None:
            return TAG_Int.from_snbt(snbt)
        elif re.compile(r'[\d.]').fullmatch(snbt) is not None:
            return TAG_Double.from_snbt(snbt)
        elif re.compile(r'[\d.]+[a-zA-Z]').fullmatch(snbt) is not None:
            typeTable = [i for i in util.all_subclasses(TAG_Number) if i.ID is not NotImplemented]

            for tagType in typeTable:
                try:
                    return tagType.from_snbt(snbt)
                except ValueError:
                    continue
            
        elif snbt[0] == '[' and snbt[-1] == ']':
            
            typeTable = [i for i in util.all_subclasses(TAG_MutableSequence) if i.ID is not NotImplemented]

            for tagType in typeTable:
                if snbt[1:3].lower() == tagType.prefix.lower():
                    return tagType.from_snbt(snbt)
            
        elif snbt[0] == '{' and snbt[-1] == '}':
            return TAG_Compound.from_snbt(snbt)
            
        else:
            raise ValueError('Invalid SNBT string')
    
    @staticmethod
    def from_ID(value):
        """Return the right TAG_Abstract subclass based on its ID"""
        IDtable = sorted(
            [i for i in util.all_subclasses(TAG_Abstract) if i.ID is not NotImplemented],
            key = lambda i : i.ID
        )
        return IDtable[value]

class TAG_End(TAG_Abstract):
    """You probably don't want to use this.
    
    Ends a TAG_Compound, expect erratic behavior if inserted inside one.
    """
    ID = 0
    valueType = None
    
    def __init__(self, value = None):
        pass
    
    @classmethod
    def from_bytes(cls, value):
        return cls(value)

    @classmethod
    def from_snbt(snbt : str):
        return cls(snbt)
    
    def to_bytes(self):
        return b'\x00'
    
    def to_snbt(self):
        return ''

class TAG_Byte(TAG_Integer):
    """UInt8 tag (0 to 255)"""
    ID = 1
    fmt = 'B'
    regex = r'[\d]+[bB]'
    suffix = 'b'

class TAG_Short(TAG_Integer):
    """Int16 tag (-32,768 to 32,767)"""
    ID = 2
    fmt = '>h'
    regex = r'[\d]+[sS]'
    suffix = 's'
  
class TAG_Int(TAG_Integer):
    """Int32 tag (-2,147,483,648 to 2,147,483,647)"""
    ID = 3
    fmt = '>i'
    regex = r'[\d]+'
    suffix = ''

class TAG_Long(TAG_Integer):
    """Int64 tag (-9,223,372,036,854,775,808 to 9,223,372,036,854,775,807)"""
    ID = 4
    fmt = '>q'
    regex = r'[\d]+[lL]'
    suffix = 'L'
 
class TAG_Float(TAG_Decimal):
    """Single precision float tag (32 bits)"""
    ID = 5
    fmt = '>f'
    regex = r'[\d.]+[fF]'
    suffix = 'f'

class TAG_Double(TAG_Decimal):
    """Double precision float tag (64 bits)"""
    ID = 6
    fmt = '>d'
    regex = r'[\d.]+[dD]?'
    suffix = 'd'

class TAG_Byte_Array(TAG_Array):
    """A TAG_Byte array
    
    Contained tags have no name
    """
    ID = 7
    elementType = TAG_Byte
    prefix = 'B;'
    
class TAG_String(TAG_Value, TAG_Sequence):
    """Unicode string tag
    
    Payload : a Short for length, then a length bytes long UTF-8 string
    """
    ID = 8
    regex = r'(?s)([\'"]).*?\1' #HERE
    #check answers on stack overflow
    #This regex needs to only match if the inner quotes are properly escaped
    valueType = str

    @classmethod
    def from_bytes(cls, iterable):
        iterator = iter(iterable)
        byteLength = TAG_Short.from_bytes(iterator)
        byteValue = util.read_bytes(iterator, n = byteLength)
        return cls( byteValue.decode(encoding='utf-8') )
    
    @classmethod
    def from_snbt(cls, snbt):
        return cls(snbt.strip('"\''))
    
    def isidentifier(self):
        return False
    
    def join(self, iterable):
        iterable = [i if isinstance(i, str) else str(i) for i in iterable]
        return self.__class__( self.value.join(iterable) )

    def partition(self, sep):
        """Partition the TAG_String into three parts using the given separator.
    
        This will search for the separator in the TAG_String.  If the separator is found,
        returns a 3-tuple containing the part before the separator, the separator
        itself, and the part after it.
            
        If the separator is not found, returns a 3-tuple containing the original TAG_String
        and two empty TAG_Strings.
        """
        return tuple( [self.__class__(i) for i in self.value.partition(sep)] )

    def rpartition(self, sep):
        return tuple( [self.__class__(i) for i in self.value.rpartition(sep)] )

    def rsplit(self, sep=None, maxsplit=-1):
        return [self.__class__(i) for i in self.value.rsplit(sep, maxsplit)]
    
    def split(self, sep=None, maxsplit=-1):
        return [self.__class__(i) for i in self.value.split(sep, maxsplit)]

    def splitlines(self, keepends=False):
        return [self.__class__(i) for i in self.value.splitlines(keepends)]
    
    def to_snbt(self):
        snbt = '"'
        
        # Escape double quotes
        for character in self.value:
            if character == '"':
                snbt += '\\"'
            else:
                snbt += character

        snbt += '"'
        return snbt

    @property
    def value(self):
        return self._value[2:].decode(encoding='utf-8')

    @value.setter
    def value(self, newValue):
        newValue = str.encode( self.valueType(newValue) )
        self._value = TAG_Short(len(newValue)).to_bytes() + newValue
   
    def __str__(self):
        return self.value

util.make_wrappers( TAG_String,
    coercedMethods = [
        'capitalize',
        'casefold',
        'center',
        'expandtabs',
        'format',
        'format_map',
        'lstrip',
        'ljust',
        'lower',
        'replace',
        'rjust',
        'rstrip',
        'strip',
        'swapcase',
        'title',
        'translate',
        'upper',
        'zfill'
    ],
    nonCoercedMethods = [
        'endswith',
        'find',
        'isalnum',
        'isalpha',
        'isascii',
        'isdecimal',
        'isdigit',
        'islower',
        'isnumeric',
        'isprintable',
        'isspace',
        'istitle',
        'isupper',
        'maketrans',
        'rfind',
        'rindex',
        'startswith'
    ]
)

class TAG_List(TAG_MutableSequence):
    """A list of tags, all of type self.elementType
    
    Type checks any additions unless it is empty
    If empty, self.elementType will be TAG_End
    """

    ID = 9
    prefix = ''

    def append(self, value):
        """Append to the list, perform type checking unless it is empty"""
        if self.elementType == TAG_End and isinstance(value, TAG_Abstract):
            self.value.append(value)
        elif self.elementType != TAG_End:
            super().append(value)
        else:
            raise ValueError('Can only append TAGs to empty TAG_List')

    @property
    def elementType(self):
        if len(self) > 0:
            return type(self[0])
        else:
            return TAG_End

    @classmethod
    def from_bytes(cls, iterable):
        iterator = iter(iterable)
        elementType = TAG.from_ID( TAG_Byte.from_bytes(iterator) )
        return cls( super().decode_bytes(iterator, elementType) )
    
    def to_bytes(self):
        return TAG_Byte(self.elementID).to_bytes() + super().to_bytes()
    
class TAG_Compound(TAG_Abstract, MutableMapping):
    """A Tag dictionary, containing other names tags of any type."""
    ID = 10
    valueType = dict

    def __init__(self, value=None):
        value = {} if value is None else value
        for i in value:
            if not isinstance(value[i], TAG_Abstract):
                raise ValueError(f'TAG_Compounds can only contain other TAGs')
        self.value = value
    
    @classmethod
    def from_bytes(cls, iterable):
        iterator = iter(iterable)
        value = {}
        
        while True:
            try:
                itemType = TAG.from_ID(TAG_Byte.from_bytes(iterator))
            except StopIteration:
                break
            
            if itemType == TAG_End:
                break

            itemName = TAG_String.from_bytes(iterator).value
            itemValue = itemType.from_bytes(iterator)
            value[itemName] = itemValue
        
        return cls(value)

    @classmethod
    def from_snbt(cls, snbt):
        value = {}
        
        for i in snbt.strip('{}').split(','):
            itemName, _, itemValue = i.partition(':')
            value[itemName] = TAG_from_snbt(itemValue)
        
        return cls(value)

    def to_bytes(self):
        encoded = bytearray()
        
        for element in self:
        
            encoded += TAG_Byte( self[element].ID ).to_bytes()
            encoded += TAG_String(element).to_bytes()
            encoded += self[element].to_bytes()
            
            if isinstance(self[element], TAG_Compound):
                encoded += TAG_End().to_bytes()
            
        return encoded

    def __repr__(self):
        return f'{{{",".join( [f"{key}:{repr(self[key])}" for key in self] )}}}'
    
    def __setitem__(self, key, value):
        """Replace self[key] with value.
        
        Value must type-compatible with self[key]
        """
        try:
            if isinstance(self[key], TAG_List) and len(self[key]) > 0:
                value = [self[key].elementType(i) for i in value]
            value = type(self[key])(value)
        except KeyError:
            pass
    
        self.value[key] = value
    
util.make_wrappers( TAG_Compound,
    nonCoercedMethods = ['__delitem__', '__getitem__', '__iter__', '__len__']
)

class TAG_Int_Array(TAG_Array):
    """A TAG_Int array
    
    Contained tags have no name
    """
    ID = 11
    elementType = TAG_Int
    prefix = 'I;'
    
class TAG_Long_Array(TAG_Array):
    """A TAG_Long array
    
    Contained tags have no name
    """
    ID = 12
    elementType = TAG_Long
    prefix = 'L;'