#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import TypeNode, SimpleTypeNode, CompoundTypeNode, NodeAttrError, \
     BuiltinType, BuiltinObject, UndefinedTypeNode
from exception import TypeChecker, SequenceTypeChecker
from exception import TypeErrorType, ValueErrorType, IndexErrorType, IOErrorType, EOFErrorType, \
     UnicodeDecodeErrorType, UnicodeEncodeErrorType
from function import ClassType, InstanceType

ANY = TypeChecker.ANY


##  BuiltinBasicType
##
class BuiltinBasicType(BuiltinType):

  # get_object()
  OBJECT = None
  @classmethod
  def get_object(klass):
    assert klass.TYPE_INSTANCE
    if not klass.OBJECT:
      klass.OBJECT = klass.TYPE_INSTANCE(klass.get_typeobj())
    return klass.OBJECT


##  BuiltinCallable
##
class BuiltinCallable(SimpleTypeNode):

  def __init__(self, name, args=None, optargs=None, expts=None):
    args = (args or [])
    optargs = (optargs or [])
    self.name = name
    self.minargs = len(args)
    self.args = args+optargs
    self.expts = (expts or [])
    SimpleTypeNode.__init__(self, self)
    return

  def __repr__(self):
    return '<callable %s>' % self.name
  
  def connect_expt(self, frame):
    return

  def process_args(self, frame, args, kwargs):
    raise NotImplementedError

  def call(self, frame, args, kwargs):
    if len(args) < self.minargs:
      frame.raise_expt(TypeErrorType.occur(
        'too few argument for %s: %d or more.' % (self.name, self.minargs)))
      return UndefinedTypeNode()
    if len(self.args) < len(args):
      frame.raise_expt(TypeErrorType.occur(
        'too many argument for %s: at most %d.' % (self.name, len(self.args))))
      return UndefinedTypeNode()
    return self.process_args(frame, args, kwargs)


##  BuiltinConstCallable
##
class BuiltinConstCallable(BuiltinCallable):
  
  def __init__(self, name, retype, args=None, optargs=None, expts=None):
    self.retype = retype
    BuiltinCallable.__init__(self, name, args=args, optargs=optargs, expts=expts)
    return

  def accept_arg(self, frame, i):
    s = 'arg%d' % i
    spec = self.args[i]
    if isinstance(spec, list):
      if spec == [ANY]:
        return SequenceTypeChecker(frame, ANY, s)
      else:
        return SequenceTypeChecker(frame, [ x.get_typeobj() for x in spec ], s)
    if isinstance(spec, tuple):
      return TypeChecker(frame, [ x.get_typeobj() for x in spec ], s)
    if spec == ANY:
      return TypeChecker(frame, ANY, s)
    return TypeChecker(frame, [spec.get_typeobj()], s)

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
    for (i,arg1) in enumerate(args):
      assert isinstance(arg1, TypeNode)
      rcpt = self.accept_arg(frame, i)
      if rcpt:
        arg1.connect(rcpt)
    for expt in self.expts:
      frame.raise_expt(expt)
    return self.retype


##  Simple Types
##
class NoneObject(BuiltinObject): pass
class NoneType(BuiltinBasicType):
  TYPE_NAME = 'NoneType'
  TYPE_INSTANCE = NoneObject

class BoolObject(BuiltinObject): pass
class BoolType(BuiltinBasicType):
  TYPE_NAME = 'bool'
  TYPE_INSTANCE = BoolObject

class NumberType(BuiltinBasicType):
  RANK = 0
  # get_rank()
  @classmethod
  def get_rank(klass):
    return klass.RANK
  
class IntObject(BuiltinObject): pass
class IntType(NumberType, BuiltinConstCallable):
  TYPE_NAME = 'int'
  TYPE_INSTANCE = IntObject
  RANK = 1

  class IntConvChecker(CompoundTypeNode):
    
    def __init__(self, frame):
      self.frame = frame
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      for obj in src:
        if obj.is_type(BaseStringType.get_typeobj()):
          self.frame.raise_expt(ValueErrorType.maybe('might be conversion error.'))
        elif obj.is_type(NumberType.get_typeobj(), BoolType.get_typeobj()):
          pass
        else:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to integer: %s' % obj))
      return

  def accept_arg(self, frame, i):
    if i == 0:
      return IntType.IntConvChecker(frame)
    else:
      return BuiltinConstCallable.accept_arg(self, frame, i)

  def __init__(self):
    IntType.TYPE = self
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'int', IntType.get_object(), [], [ANY, IntType])
    return
  
class LongObject(BuiltinObject): pass
class LongType(IntType):
  TYPE_NAME = 'long'
  TYPE_INSTANCE = LongObject
  RANK = 2

class FloatObject(BuiltinObject): pass
class FloatType(NumberType):
  TYPE_NAME = 'float'
  TYPE_INSTANCE = FloatObject
  RANK = 3
  
class ComplexObject(BuiltinObject): pass
class ComplexType(NumberType):
  TYPE_NAME = 'complex'
  TYPE_INSTANCE = ComplexObject
  RANK = 4


##  Strings
##
class BaseStringObject(BuiltinObject):
  
  def get_iter(self, frame):
    from aggregate_types import IterType
    return IterType.create_iter(self)

  def get_element(self, frame, subs, write=False):
    if write:
      frame.raise_expt(TypeErrorType.occur('cannot change a string.'))
    else:
      frame.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self

class BaseStringType(BuiltinBasicType, BuiltinConstCallable):
  TYPE_NAME = 'basestring'

  def get_attr(self, name, write=False):
    from aggregate_types import TupleType, ListType
    if name == 'capitalize':
      return BuiltinConstCallable('str.capitalize', self.get_object())
    elif name == 'center':
      return BuiltinConstCallable('str.center', self.get_object(),
                               [IntType], [BaseStringType])
    elif name == 'count':
      return BuiltinConstCallable('str.count', IntType.get_object(),
                               [BaseStringType], [IntType, IntType])
    elif name == 'decode':
      return BuiltinConstCallable('str.decode', UnicodeType.get_object(),
                               [], [BaseStringType, BaseStringType],
                               [UnicodeDecodeErrorType.maybe('might not able to decode.')])
    elif name == 'encode':
      return BuiltinConstCallable('str.encode', StrType.get_object(),
                               [], [BaseStringType, BaseStringType],
                               [UnicodeDecodeErrorType.maybe('might not able to encode.')])
    elif name == 'endswith':
      return BuiltinConstCallable('str.endswith', BoolType.get_object(),
                               [BaseStringType], [IntType, IntType])
    elif name == 'expandtabs':
      return BuiltinConstCallable('str.expandtabs', self.get_object(),
                               [], [IntType])
    elif name == 'find':
      return BuiltinConstCallable('str.find', IntType.get_object(),
                               [BaseStringType], [IntType, IntType])
    elif name == 'index':
      return BuiltinConstCallable('str.index', IntType.get_object(),
                               [BaseStringType], [IntType, IntType],
                               [ValueErrorType.maybe('might not able to find the substring.')])
    elif name == 'isalnum':
      return BuiltinConstCallable('str.isalnum', BoolType.get_object())
    elif name == 'isalpha':
      return BuiltinConstCallable('str.isalpha', BoolType.get_object())
    elif name == 'isdigit':
      return BuiltinConstCallable('str.isdigit', BoolType.get_object())
    elif name == 'islower':
      return BuiltinConstCallable('str.islower', BoolType.get_object())
    elif name == 'isspace':
      return BuiltinConstCallable('str.isspace', BoolType.get_object())
    elif name == 'istitle':
      return BuiltinConstCallable('str.istitle', BoolType.get_object())
    elif name == 'isupper':
      return BuiltinConstCallable('str.isupper', BoolType.get_object())
    elif name == 'join':
      return BuiltinConstCallable('str.join', self.get_object(),
                               [[BaseStringType]])
    elif name == 'ljust':
      return BuiltinConstCallable('str.ljust', self.get_object(),
                               [IntType], [BaseStringType])
    elif name == 'lower':
      return BuiltinConstCallable('str.lower', self.get_object())
    elif name == 'lstrip':
      return BuiltinConstCallable('str.lstrip', self.get_object(),
                               [BaseStringType])
    elif name == 'partition':
      return BuiltinConstCallable('str.partiion',
                               TupleType.create_tuple([self.get_object(), self.get_object(), self.get_object()]),
                               [BaseStringType])
    elif name == 'replace':
      return BuiltinConstCallable('str.replace', self.get_object(),
                               [BaseStringType, BaseStringType], [IntType])
    elif name == 'rfind':
      return BuiltinConstCallable('str.rfind', IntType.get_object(),
                               [BaseStringType], [IntType, IntType])
    elif name == 'rindex':
      return BuiltinConstCallable('str.rindex', IntType.get_object(),
                               [BaseStringType], [IntType, IntType],
                               [ValueErrorType.maybe('might not able to find the substring.')])
    elif name == 'rjust':
      return BuiltinConstCallable('str.rjust', self.get_object(),
                               [IntType], [BaseStringType])
    elif name == 'rpartition':
      return BuiltinConstCallable('str.rpartiion',
                               TupleType.create_tuple([self.get_object(), self.get_object(), self.get_object()]),
                               [BaseStringType])
    elif name == 'rsplit':
      return BuiltinConstCallable('str.rsplit', ListType.create_sequence(self.get_object()),
                               [], [BaseStringType, IntType])
    elif name == 'rstrip':
      return BuiltinConstCallable('str.rstrip', self.get_object(),
                               [BaseStringType])
    elif name == 'split':
      return BuiltinConstCallable('str.split', ListType.create_sequence(self.get_object()),
                               [], [BaseStringType, IntType])
    elif name == 'splitlines':
      return BuiltinConstCallable('str.splitlines', ListType.create_sequence(self.get_object()),
                               [], [ANY])
    elif name == 'startswith':
      return BuiltinConstCallable('str.startswith', BoolType.get_object(),
                              [BaseStringType], [IntType, IntType])
    elif name == 'strip':
      return BuiltinConstCallable('str.strip', self.get_object(),
                               [BaseStringType])
    elif name == 'swapcase':
      return BuiltinConstCallable('str.swapcase', self.get_object())
    elif name == 'title':
      return BuiltinConstCallable('str.title', self.get_object())
    elif name == 'upper':
      return BuiltinConstCallable('str.upper', self.get_object())
    elif name == 'zfill':
      return BuiltinConstCallable('str.zfill', self.get_object(),
                               [IntType])
    raise NodeAttrError(name)

  class StrConvChecker(CompoundTypeNode):
    
    def __init__(self, frame):
      self.frame = frame
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      for obj in src:
        if obj.is_type(InstanceType.get_typeobj()):
          value = obj.get_attr('__str__').optcall(self.frame, (), {})
          value.connect(TypeChecker(self.frame, BaseStringType.get_typeobj(), 
                                    'the return value of __str__ method'))
          value = obj.get_attr('__repr__').optcall(self.frame, (), {})
          value.connect(TypeChecker(self.frame, BaseStringType.get_typeobj(), 
                                    'the return value of __repr__ method'))
      return

  def accept_arg(self, frame, _):
    return BaseStringType.StrConvChecker(frame)

  def call(self, frame, args, kwargs):
    if self.TYPE_NAME == 'basestring':
      frame.raise_expt(TypeErrorType.occur('cannot instantiate a basestring type.'))
      return UndefinedTypeNode()
    return BuiltinConstCallable.call(self, frame, args, kwargs)

  def create_sequence(self, elemall=None):
    return self.get_object()
  
  def __init__(self):
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'basestring', None)
    return
  
class StrObject(BaseStringObject): pass
class StrType(BaseStringType):
  TYPE_NAME = 'str'
  TYPE_INSTANCE = StrObject
  
  def get_attr(self, name, write=False):
    if name == 'translate':
      return BuiltinConstCallable('str.translate', self.get_object(),
                               [BaseStringType], [BaseStringType],
                               [ValueErrorType.maybe('table might not be 256 chars long.')])
    return BaseStringType.get_attr(self, name, write=write)
    
  def __init__(self):
    StrType.TYPE = self
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'str', StrType.get_object(), [], [ANY])
    return

class UnicodeObject(BaseStringObject): pass
class UnicodeType(BaseStringType):
  TYPE_NAME = 'unicode'
  TYPE_INSTANCE = UnicodeObject

  class TranslateFunc(BuiltinConstCallable):
    def accept_arg(self, frame, i):
      return KeyValueTypeChecker(frame,
                                 [IntType.get_typeobj()],
                                 [IntType.get_typeobj(), UnicodeType.get_typeobj(), NoneType.get_typeobj()],
                                 'arg%d' % i)

  def get_attr(self, name, write=False):
    if name == 'isdecimal':
      return BuiltinConstCallable('unicode.isdecimal', BoolType.get_object())
    elif name == 'isnumeric':
      return BuiltinConstCallable('unicode.isnumeric', BoolType.get_object())
    elif name == 'translate':
      return self.TranslateFunc('unicode.translate', self.get_object(),
                                [ANY])
    return BaseStringType.get_attr(self, name, write=write)

  def __init__(self):
    UnicodeType.TYPE = self
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'unicode', UnicodeType.get_object(),
                               [], [ANY])
    return
  

##  FileType
##
class FileObject(BuiltinObject):
  def get_iter(self, frame):
    from aggregate_types import IterType
    return IterType.create_iter(StrType.get_object())
  
class FileType(BuiltinBasicType, BuiltinConstCallable):
  TYPE_NAME = 'file'
  TYPE_INSTANCE = FileObject
  
  def __init__(self):
    FileType.TYPE = self
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'file', FileType.get_object(),
                               [StrType], [StrType, IntType],
                               [IOErrorType.maybe('might not able to open a file.')])
    return

  def get_attr(self, name, write=False):
    from aggregate_types import ListType
    if name == 'close':
      return BuiltinConstCallable('file.close', NoneType.get_object())
    elif name == 'closed':
      return BoolType.get_object()
    elif name == 'encoding':
      return StrType.get_object()
    elif name == 'fileno':
      return BuiltinConstCallable('file.fileno', IntType.get_object())
    elif name == 'flush':
      return BuiltinConstCallable('file.flush', NoneType.get_object())
    elif name == 'isatty':
      return BuiltinConstCallable('file.isatty', BoolType.get_object())
    elif name == 'mode':
      return StrType.get_object()
    elif name == 'name':
      return StrType.get_object()
    elif name == 'newlines':
      return NoneType.get_object()
    elif name == 'next':
      return BuiltinConstCallable('file.next', StrType.get_object())
    elif name == 'read':
      return BuiltinConstCallable('file.read', StrType.get_object(),
                               [], [IntType],
                               [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'readline':
      return BuiltinConstCallable('file.readline', StrType.get_object(),
                               [], [IntType],
                               [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'readlines':
      return BuiltinConstCallable('file.readlines', ListType.create_sequence(StrType.get_object()),
                               [], [IntType],
                               [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'seek':
      return BuiltinConstCallable('file.seek', NoneType.get_object(),
                               [IntType], [IntType],
                               [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'softspace':
      return IntType.get_object()
    elif name == 'tell':
      return BuiltinConstCallable('file.tell', IntType.get_object(),
                               expts=[IOErrorType.maybe('might be an illegal seek.')])
    elif name == 'truncate':
      return BuiltinConstCallable('file.truncate', NoneType.get_object(),
                               [], [IntType])
    elif name == 'write':
      return BuiltinConstCallable('file.write', NoneType.get_object(),
                               [BaseStringType])
    elif name == 'writelines':
      return BuiltinConstCallable('file.writestrings', NoneType.get_object(),
                               [[BaseStringType]])
    elif name == 'xreadlines':
      return self
    raise NodeAttrError(name)


##  ObjectType
##
class ObjectObject(BuiltinObject): pass
class ObjectType(BuiltinBasicType, BuiltinConstCallable):
  TYPE_NAME = 'object'
  TYPE_INSTANCE = ObjectObject
  
  def __init__(self):
    ObjectType.TYPE = self
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'object', ObjectType.get_object())
    return

##  TypeType
##
class TypeType(BuiltinBasicType):
  TYPE_NAME = 'type'



#
BUILTIN_OBJECTS = dict(
  (cls.get_name(), cls.get_object()) for cls in
  ( NoneType, BoolType, IntType, LongType, FloatType, ComplexType, StrType, UnicodeType )
  )

