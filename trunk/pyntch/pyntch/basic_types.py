#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import TypeNode, CompoundTypeNode, NodeAttrError, \
     BuiltinType, BuiltinBasicType, BuiltinObject, UndefinedTypeNode
from exception import TypeChecker, SequenceTypeChecker
from exception import TypeErrorType, ValueErrorType, IndexErrorType, IOErrorType, EOFErrorType, \
     UnicodeDecodeErrorType, UnicodeEncodeErrorType
from klass import InstanceObject

ANY = TypeChecker.ANY


##  BuiltinCallable
##
##  A helper class to augment builtin objects (mostly type objects)
##  for behaving like a function.
##
class BuiltinCallable(object):

  def __init__(self, name, args=None, optargs=None, expts=None):
    args = (args or [])
    optargs = (optargs or [])
    self.name = name
    self.minargs = len(args)
    self.args = args+optargs
    self.expts = (expts or [])
    return
  
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

  def process_args(self, frame, args, kwargs):
    raise NotImplementedError


##  BuiltinConstCallable
##
class BuiltinConstCallable(BuiltinCallable):
  
  def __init__(self, name, retobj, args=None, optargs=None, expts=None):
    self.retobj = retobj
    BuiltinCallable.__init__(self, name, args=args, optargs=optargs, expts=expts)
    return

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
    for (i,arg1) in enumerate(args):
      assert isinstance(arg1, TypeNode)
      self.accept_arg(frame, i, arg1)
    for expt in self.expts:
      frame.raise_expt(expt)
    return self.retobj

  def accept_arg(self, frame, i, arg1):
    s = 'arg%d' % i
    spec = self.args[i]
    if isinstance(spec, list):
      if spec == [ANY]:
        arg1.connect(SequenceTypeChecker(frame, ANY, s))
      else:
        arg1.connect(SequenceTypeChecker(frame, [ x.get_typeobj() for x in spec ], s))
    elif isinstance(spec, tuple):
      arg1.connect(TypeChecker(frame, [ x.get_typeobj() for x in spec ], s))
    elif spec == ANY:
      arg1.connect(TypeChecker(frame, ANY, s))
    else:
      arg1.connect(TypeChecker(frame, [spec.get_typeobj()], s))
    return


##  BuiltinConstMethod
##
class BuiltinMethodType(BuiltinType):
  TYPE_NAME = 'builtin_method'
  
class BuiltinConstMethod(BuiltinConstCallable, BuiltinObject):

  def __init__(self, name, retobj, args=None, optargs=None, expts=None):
    BuiltinObject.__init__(self, BuiltinMethodType.get_typeobj())
    BuiltinConstCallable.__init__(self, name, retobj, args=args, optargs=optargs, expts=expts)
    return

  def __repr__(self):
    return '<callable %s>' % self.name


##  TypeType
##
class TypeType(BuiltinType, BuiltinConstCallable):
  TYPE_NAME = 'type'

  def __init__(self):
    BuiltinType.__init__(self)
    # type() funciton returns itself.
    BuiltinConstCallable.__init__(self, 'type', self, [ANY])
    return


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
  TYPE_NAME = 'number'
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
      self.done = set()
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        if obj.is_type(BaseStringType.get_typeobj()):
          self.frame.raise_expt(ValueErrorType.maybe('might be conversion error.'))
        elif obj.is_type(NumberType.get_typeobj(), BoolType.get_typeobj()):
          pass
        else:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to integer: %s' % obj))
      return

  def accept_arg(self, frame, i, arg1):
    if i == 0:
      arg1.connect(IntType.IntConvChecker(frame))
    else:
      BuiltinConstCallable.accept_arg(self, frame, i, arg1)
    return

  def __init__(self):
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'int', self.get_object(), [], [ANY, IntType])
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

  def __init__(self, typeobj):
    self.iter = None
    BuiltinObject.__init__(self, typeobj)
    return
  
  def get_iter(self, frame):
    from aggregate_types import IterType
    if not self.iter:
      self.iter = IterType.create_iter(self)
    return self.iter

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
      return BuiltinConstMethod('str.capitalize', self.get_object())
    elif name == 'center':
      return BuiltinConstMethod('str.center', self.get_object(),
                                [IntType], [BaseStringType])
    elif name == 'count':
      return BuiltinConstMethod('str.count', IntType.get_object(),
                                [BaseStringType], [IntType, IntType])
    elif name == 'decode':
      return BuiltinConstMethod('str.decode', UnicodeType.get_object(),
                                [], [BaseStringType, BaseStringType],
                                [UnicodeDecodeErrorType.maybe('might not able to decode.')])
    elif name == 'encode':
      return BuiltinConstMethod('str.encode', StrType.get_object(),
                                [], [BaseStringType, BaseStringType],
                                [UnicodeDecodeErrorType.maybe('might not able to encode.')])
    elif name == 'endswith':
      return BuiltinConstMethod('str.endswith', BoolType.get_object(),
                                [BaseStringType], [IntType, IntType])
    elif name == 'expandtabs':
      return BuiltinConstMethod('str.expandtabs', self.get_object(),
                                [], [IntType])
    elif name == 'find':
      return BuiltinConstMethod('str.find', IntType.get_object(),
                                [BaseStringType], [IntType, IntType])
    elif name == 'index':
      return BuiltinConstMethod('str.index', IntType.get_object(),
                                [BaseStringType], [IntType, IntType],
                                [ValueErrorType.maybe('might not able to find the substring.')])
    elif name == 'isalnum':
      return BuiltinConstMethod('str.isalnum', BoolType.get_object())
    elif name == 'isalpha':
      return BuiltinConstMethod('str.isalpha', BoolType.get_object())
    elif name == 'isdigit':
      return BuiltinConstMethod('str.isdigit', BoolType.get_object())
    elif name == 'islower':
      return BuiltinConstMethod('str.islower', BoolType.get_object())
    elif name == 'isspace':
      return BuiltinConstMethod('str.isspace', BoolType.get_object())
    elif name == 'istitle':
      return BuiltinConstMethod('str.istitle', BoolType.get_object())
    elif name == 'isupper':
      return BuiltinConstMethod('str.isupper', BoolType.get_object())
    elif name == 'join':
      return BuiltinConstMethod('str.join', self.get_object(),
                                [[BaseStringType]])
    elif name == 'ljust':
      return BuiltinConstMethod('str.ljust', self.get_object(),
                                [IntType], [BaseStringType])
    elif name == 'lower':
      return BuiltinConstMethod('str.lower', self.get_object())
    elif name == 'lstrip':
      return BuiltinConstMethod('str.lstrip', self.get_object(),
                                [BaseStringType])
    elif name == 'partition':
      return BuiltinConstMethod('str.partiion',
                                TupleType.create_tuple([self.get_object(), self.get_object(), self.get_object()]),
                                [BaseStringType])
    elif name == 'replace':
      return BuiltinConstMethod('str.replace', self.get_object(),
                                [BaseStringType, BaseStringType], [IntType])
    elif name == 'rfind':
      return BuiltinConstMethod('str.rfind', IntType.get_object(),
                                [BaseStringType], [IntType, IntType])
    elif name == 'rindex':
      return BuiltinConstMethod('str.rindex', IntType.get_object(),
                                [BaseStringType], [IntType, IntType],
                                [ValueErrorType.maybe('might not able to find the substring.')])
    elif name == 'rjust':
      return BuiltinConstMethod('str.rjust', self.get_object(),
                           [IntType], [BaseStringType])
    elif name == 'rpartition':
      return BuiltinConstMethod('str.rpartiion',
                           TupleType.create_tuple([self.get_object(), self.get_object(), self.get_object()]),
                           [BaseStringType])
    elif name == 'rsplit':
      return BuiltinConstMethod('str.rsplit', ListType.create_list(self.get_object()),
                           [], [BaseStringType, IntType])
    elif name == 'rstrip':
      return BuiltinConstMethod('str.rstrip', self.get_object(),
                           [BaseStringType])
    elif name == 'split':
      return BuiltinConstMethod('str.split', ListType.create_list(self.get_object()),
                           [], [BaseStringType, IntType])
    elif name == 'splitlines':
      return BuiltinConstMethod('str.splitlines', ListType.create_list(self.get_object()),
                           [], [ANY])
    elif name == 'startswith':
      return BuiltinConstMethod('str.startswith', BoolType.get_object(),
                           [BaseStringType], [IntType, IntType])
    elif name == 'strip':
      return BuiltinConstMethod('str.strip', self.get_object(),
                           [BaseStringType])
    elif name == 'swapcase':
      return BuiltinConstMethod('str.swapcase', self.get_object())
    elif name == 'title':
      return BuiltinConstMethod('str.title', self.get_object())
    elif name == 'upper':
      return BuiltinConstMethod('str.upper', self.get_object())
    elif name == 'zfill':
      return BuiltinConstMethod('str.zfill', self.get_object(),
                           [IntType])
    raise NodeAttrError(name)

  class StrConvChecker(CompoundTypeNode):
    
    def __init__(self, frame):
      self.frame = frame
      self.done = set()
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      from expression import MethodCall
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        if isinstance(obj, InstanceObject):
          value = MethodCall(self.frame, obj, '__str__', (), {})
          value.connect(TypeChecker(self.frame, BaseStringType.get_typeobj(), 
                                    'the return value of __str__ method'))
          value = MethodCall(self.frame, obj, '__repr__', (), {})
          value.connect(TypeChecker(self.frame, BaseStringType.get_typeobj(), 
                                    'the return value of __repr__ method'))
      return

  def accept_arg(self, frame, i, arg1):
    arg1.connect(self.StrConvChecker(frame))
    return

  def call(self, frame, args, kwargs):
    if self.TYPE_NAME == 'basestring':
      frame.raise_expt(TypeErrorType.occur('cannot instantiate a basestring type.'))
      return UndefinedTypeNode()
    return BuiltinConstCallable.call(self, frame, args, kwargs)

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
      return BuiltinConstMethod('str.translate', self.get_object(),
                           [BaseStringType], [BaseStringType],
                           [ValueErrorType.maybe('table might not be 256 chars long.')])
    return BaseStringType.get_attr(self, name, write=write)
    
  def __init__(self):
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'str', self.get_object(), [], [ANY])
    return

class UnicodeObject(BaseStringObject): pass
class UnicodeType(BaseStringType):
  TYPE_NAME = 'unicode'
  TYPE_INSTANCE = UnicodeObject

  class TranslateFunc(BuiltinConstMethod):
    def accept_arg(self, frame, i, arg1):
      arg1.connect(KeyValueTypeChecker(frame,
                                       [IntType.get_typeobj()],
                                       [IntType.get_typeobj(), UnicodeType.get_typeobj(), NoneType.get_typeobj()],
                                       'arg%d' % i))
      return

  def get_attr(self, name, write=False):
    if name == 'isdecimal':
      return BuiltinConstMethod('unicode.isdecimal', BoolType.get_object())
    elif name == 'isnumeric':
      return BuiltinConstMethod('unicode.isnumeric', BoolType.get_object())
    elif name == 'translate':
      return self.TranslateFunc('unicode.translate', self.get_object(),
                                [ANY])
    return BaseStringType.get_attr(self, name, write=write)

  def __init__(self):
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'unicode', self.get_object(), [], [ANY])
    return
  

##  FileType
##
class FileObject(BuiltinObject):

  def __init__(self, typeobj):
    self.iter = None
    BuiltinObject.__init__(self, typeobj)
    return
  
  def get_iter(self, frame):
    from aggregate_types import IterType
    if not self.iter:
      self.iter = IterType.create_iter(StrType.get_object())
    return self.iter
  
class FileType(BuiltinBasicType, BuiltinConstCallable):
  TYPE_NAME = 'file'
  TYPE_INSTANCE = FileObject
  
  def __init__(self):
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'file', self.get_object(),
                                  [StrType], [StrType, IntType],
                                  [IOErrorType.maybe('might not able to open a file.')])
    return

  def get_attr(self, name, write=False):
    from aggregate_types import ListType
    if name == 'close':
      return BuiltinConstMethod('file.close', NoneType.get_object())
    elif name == 'closed':
      return BoolType.get_object()
    elif name == 'encoding':
      return StrType.get_object()
    elif name == 'fileno':
      return BuiltinConstMethod('file.fileno', IntType.get_object())
    elif name == 'flush':
      return BuiltinConstMethod('file.flush', NoneType.get_object())
    elif name == 'isatty':
      return BuiltinConstMethod('file.isatty', BoolType.get_object())
    elif name == 'mode':
      return StrType.get_object()
    elif name == 'name':
      return StrType.get_object()
    elif name == 'newlines':
      return NoneType.get_object()
    elif name == 'next':
      return BuiltinConstMethod('file.next', StrType.get_object())
    elif name == 'read':
      return BuiltinConstMethod('file.read', StrType.get_object(),
                           [], [IntType],
                           [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'readline':
      return BuiltinConstMethod('file.readline', StrType.get_object(),
                           [], [IntType],
                           [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'readlines':
      return BuiltinConstMethod('file.readlines', ListType.create_list(StrType.get_object()),
                           [], [IntType],
                           [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'seek':
      return BuiltinConstMethod('file.seek', NoneType.get_object(),
                           [IntType], [IntType],
                           [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'softspace':
      return IntType.get_object()
    elif name == 'tell':
      return BuiltinConstMethod('file.tell', IntType.get_object(),
                           expts=[IOErrorType.maybe('might be an illegal seek.')])
    elif name == 'truncate':
      return BuiltinConstMethod('file.truncate', NoneType.get_object(),
                           [], [IntType])
    elif name == 'write':
      return BuiltinConstMethod('file.write', NoneType.get_object(),
                           [BaseStringType])
    elif name == 'writelines':
      return BuiltinConstMethod('file.writestrings', NoneType.get_object(),
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
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'object', self.get_object())
    return

BUILTIN_OBJECT = dict(
  (cls.get_name(), cls.get_object()) for cls in
  ( NoneType, BoolType, IntType, LongType, FloatType, ComplexType, StrType, UnicodeType, FileType ))

