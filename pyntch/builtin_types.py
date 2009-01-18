#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import TypeNode, SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, UndefinedTypeNode
from exception import ExceptionType, ExceptionRaiser, TypeChecker, ElementTypeChecker
from function import KeywordArg, ClassType, InstanceType

ANY_TYPE = False


##  BuiltinType
##
class BuiltinType(SimpleTypeNode):

  PYTHON_TYPE = 'undefined'
  
  def __init__(self):
    SimpleTypeNode.__init__(self, self)
    return

  def __repr__(self):
    return '<type %s>' % self.get_name()

  # get_name()
  # returns the name of the Python type of this object.
  @classmethod
  def get_name(klass):
    return klass.PYTHON_TYPE.__name__

  # get_type()
  TYPE = None
  @classmethod
  def get_type(klass):
    if not klass.TYPE:
      klass.TYPE = klass()
    return klass.TYPE

  # get_object()
  OBJECT = None
  @classmethod
  def get_object(klass):
    if not klass.OBJECT:
      klass.OBJECT = SimpleTypeNode(klass.get_type())
    return klass.OBJECT


##  BuiltinFunc
##
class BuiltinFunc(SimpleTypeNode):

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
    return '<builtin %s>' % self.name

  @classmethod
  def get_typename(klass):
    return 'builtin'
  
  def connect_expt(self, frame):
    return

  def process_args(self, caller, args):
    raise NotImplementedError
  
  def call(self, caller, args):
    if len(args) < self.minargs:
      caller.raise_expt(ExceptionType(
        'TypeError',
        'too few argument for %s: %d or more' % (self.name, self.minargs)))
      return UndefinedTypeNode()
    if len(self.args) < len(args):
      caller.raise_expt(ExceptionType(
        'TypeError',
        'too many argument for %s: at most %d' % (self.name, len(self.args))))
      return UndefinedTypeNode()
    return self.process_args(caller, args)


##  BuiltinConstFunc
##
class BuiltinConstFunc(BuiltinFunc):
  
  def __init__(self, name, retype, args=None, optargs=None, expts=None):
    self.retype = retype
    BuiltinFunc.__init__(self, name, args=args, optargs=optargs, expts=expts)
    return

  def accept_arg(self, caller, i):
    if self.args[i]:
      return TypeChecker(caller, self.args[i].get_type(), caller.loc, 'arg%d' % i)
    else:
      return None

  def process_args(self, caller, args):
    for (i,arg1) in enumerate(args):
      if isinstance(arg1, KeywordArg):
        caller.raise_expt(ExceptionType(
          'TypeError',
          'cannot take keyword argument: %r' % arg1.name))
      else:
        assert isinstance(arg1, TypeNode)
        rcpt = self.accept_arg(caller, i)
        if rcpt:
          arg1.connect(rcpt)
    for expt in self.expts:
      caller.raise_expt(expt)
    return self.retype


##  Simple Types
##
class NoneType(BuiltinType):
  PYTHON_TYPE = type(None)

class BoolType(BuiltinType):
  PYTHON_TYPE = bool

class NumberType(BuiltinType):
  RANK = 0
  # get_rank()
  @classmethod
  def get_rank(klass):
    return klass.RANK
  
class IntType(NumberType, BuiltinConstFunc):
  PYTHON_TYPE = int
  RANK = 1

  class IntConversion(CompoundTypeNode):
    
    def __init__(self, parent_frame):
      CompoundTypeNode.__init__(self)
      self.parent_frame = parent_frame
      return
    
    def recv(self, src):
      for obj in src.types:
        if obj.is_type(BaseStringType.get_type()):
          self.parent_frame.raise_expt(ExceptionType(
            'ValueError',
            'might be conversion error'))
        elif obj.is_type((NumberType.get_type(), BoolType.get_type())):
          pass
        else:
          self.parent_frame.raise_expt(ExceptionType(
            'TypeError',
            'cannot convert to integer: %s' % obj))
      return

  def accept_arg(self, caller, i):
    if i == 0:
      return self.IntConversion(caller)
    else:
      return BuiltinConstFunc.accept_arg(self, caller, i)

  def __init__(self):
    IntType.TYPE = self
    BuiltinConstFunc.__init__(self, 'int', IntType.get_object(),
                              [],
                              [ANY_TYPE, IntType])
    return
  
class LongType(IntType):
  PYTHON_TYPE = long
  RANK = 2
  
class FloatType(NumberType):
  PYTHON_TYPE = float
  RANK = 3
  
class ComplexType(NumberType):
  PYTHON_TYPE = complex
  RANK = 4

class BaseStringType(BuiltinType, BuiltinConstFunc):
  PYTHON_TYPE = basestring

  class JoinFunc(BuiltinConstFunc):
    def accept_arg(self, caller, i):
      return ElementTypeChecker(caller, self.args[i].get_type(), caller.loc, 'arg%d' % i)

  def get_attr(self, name):
    from aggregate_types import TupleObject, ListObject
    if name == 'capitalize':
      return BuiltinConstFunc('str.capitalize', self.get_object())
    elif name == 'center':
      return BuiltinConstFunc('str.center', self.get_object(),
                         [IntType], 
                         [BaseStringType])
    elif name == 'count':
      return BuiltinConstFunc('str.count', IntType.get_object(),
                         [BaseStringType],
                         [IntType, IntType])
    elif name == 'decode':
      return BuiltinConstFunc('str.decode', UnicodeType.get_object(),
                         [],
                         [BaseStringType, BaseStringType],
                         [ExceptionType('UnicodeDecodeError', 'might not able to decode')])
    elif name == 'encode':
      return BuiltinConstFunc('str.encode', StrType.get_object(),
                         [],
                         [BaseStringType, BaseStringType],
                         [ExceptionType('UnicodeEncodeError', 'might not able to encode')])
    elif name == 'endswith':
      return BuiltinConstFunc('str.endswith', BoolType.get_object(),
                         [BaseStringType],
                         [IntType, IntType])
    elif name == 'expandtabs':
      return BuiltinConstFunc('str.expandtabs', self.get_object(),
                         [],
                         [IntType])
    elif name == 'find':
      return BuiltinConstFunc('str.find', IntType.get_object(),
                         [BaseStringType],
                         [IntType, IntType])
    elif name == 'index':
      return BuiltinConstFunc('str.index', IntType.get_object(),
                         [BaseStringType],
                         [IntType, IntType],
                         [ExceptionType('ValueError', 'might not able to find the substring')])
    elif name == 'isalnum':
      return BuiltinConstFunc('str.isalnum', BoolType.get_object())
    elif name == 'isalpha':
      return BuiltinConstFunc('str.isalpha', BoolType.get_object())
    elif name == 'isdigit':
      return BuiltinConstFunc('str.isdigit', BoolType.get_object())
    elif name == 'islower':
      return BuiltinConstFunc('str.islower', BoolType.get_object())
    elif name == 'isspace':
      return BuiltinConstFunc('str.isspace', BoolType.get_object())
    elif name == 'istitle':
      return BuiltinConstFunc('str.istitle', BoolType.get_object())
    elif name == 'isupper':
      return BuiltinConstFunc('str.isupper', BoolType.get_object())
    elif name == 'join':
      return self.JoinFunc('str.join', self.get_object(),
                           [BaseStringType])
    elif name == 'ljust':
      return BuiltinConstFunc('str.ljust', self.get_object(),
                         [IntType], 
                         [BaseStringType])
    elif name == 'lower':
      return BuiltinConstFunc('str.lower', self.get_object())
    elif name == 'lstrip':
      return BuiltinConstFunc('str.lstrip', self.get_object(),
                         [BaseStringType])
    elif name == 'partition':
      return BuiltinConstFunc('str.partiion', TupleObject([self.get_object(), self.get_object(), self.get_object()]),
                         [BaseStringType])
    elif name == 'replace':
      return BuiltinConstFunc('str.replace', self.get_object(),
                         [BaseStringType, BaseStringType], [IntType])
    elif name == 'rfind':
      return BuiltinConstFunc('str.rfind', IntType.get_object(),
                         [BaseStringType],
                         [IntType, IntType])
    elif name == 'rindex':
      return BuiltinConstFunc('str.rindex', IntType.get_object(),
                         [BaseStringType],
                         [IntType, IntType],
                         [ExceptionType('ValueError', 'might not able to find the substring')])
    elif name == 'rjust':
      return BuiltinConstFunc('str.rjust', self.get_object(),
                         [IntType], 
                         [BaseStringType])
    elif name == 'rpartition':
      return BuiltinConstFunc('str.rpartiion', TupleObject([self.get_object(), self.get_object(), self.get_object()]),
                         [BaseStringType])
    elif name == 'rsplit':
      return BuiltinConstFunc('str.rsplit', ListObject([self.get_object()]),
                         [],
                         [BaseStringType, IntType])
    elif name == 'rstrip':
      return BuiltinConstFunc('str.rstrip', self.get_object(),
                         [BaseStringType])
    elif name == 'split':
      return BuiltinConstFunc('str.split', ListObject([self.get_object()]),
                         [],
                         [BaseStringType, IntType])
    elif name == 'splitlines':
      return BuiltinConstFunc('str.splitlines', ListObject([self.get_object()]),
                         [],
                         [ANY_TYPE])
    elif name == 'startswith':
      return BuiltinConstFunc('str.startswith', BoolType.get_object(),
                         [BaseStringType],
                         [IntType, IntType])
    elif name == 'strip':
      return BuiltinConstFunc('str.strip', self.get_object(),
                         [BaseStringType])
    elif name == 'swapcase':
      return BuiltinConstFunc('str.swapcase', self.get_object())
    elif name == 'title':
      return BuiltinConstFunc('str.title', self.get_object())
    elif name == 'upper':
      return BuiltinConstFunc('str.upper', self.get_object())
    elif name == 'zfill':
      return BuiltinConstFunc('str.zfill', self.get_object(),
                         [IntType])
    raise NodeAttrError(name)

  def get_iter(self, caller):
    return self.get_object()

  class StrConversion(CompoundTypeNode, ExceptionRaiser):
    
    def __init__(self, parent_frame, loc):
      CompoundTypeNode.__init__(self)
      ExceptionRaiser.__init__(self, parent_frame, loc)
      return
    
    def recv(self, src):
      for obj in src.types:
        if isinstance(obj, InstanceType):
          value = ClassType.OptionalAttr(obj, '__str__').call(self, ())
          value.connect(TypeChecker(self, BaseStringType.get_type(), self.loc, 'the return value of __str__ method'))
          value = ClassType.OptionalAttr(obj, '__repr__').call(self, ())
          value.connect(TypeChecker(self, BaseStringType.get_type(), self.loc, 'the return value of __repr__ method'))
      return

  def accept_arg(self, caller, _):
    return self.StrConversion(caller, caller.loc)

  def call(self, caller, args):
    if self.PYTHON_TYPE is basestring:
      caller.raise_expt(ExceptionType(
        'TypeError',
        'cannot instantiate a basestring type'))
      return UndefinedTypeNode()
    return BuiltinConstFunc.call(self, caller, args)
  
  def __init__(self):
    BuiltinConstFunc.__init__(self, 'basestring', None)
    return
  
class StrType(BaseStringType):
  PYTHON_TYPE = str
  
  def get_attr(self, name):
    if name == 'translate':
      return BuiltinConstFunc('str.translate', self.get_object(),
                         [BaseStringType],
                         [BaseStringType],
                         [ExceptionType('ValueError', 'table must be 256 chars long')])
    return BaseStringType.get_attr(self, name)
    
  def __init__(self):
    StrType.TYPE = self
    BuiltinConstFunc.__init__(self, 'str', StrType.get_object(),
                              [],
                              [ANY_TYPE])
    return
  
class UnicodeType(BaseStringType):
  PYTHON_TYPE = unicode

  def get_attr(self, name):
    if name == 'isdecimal':
      return BuiltinConstFunc('unicode.isdecimal', BoolType.get_object())
    elif name == 'isnumeric':
      return BuiltinConstFunc('unicode.isnumeric', BoolType.get_object())
    elif name == 'translate':
      return XXX
      return BuiltinConstFunc('unicode.translate', self.get_object(),
                         [BaseStringType])
    return BaseStringType.get_attr(self, name)

  def __init__(self):
    UnicodeType.TYPE = self
    BuiltinConstFunc.__init__(self, 'unicode', UnicodeType.get_object(),
                              [],
                              [ANY_TYPE])
    return
  

##  FileType
##
class FileType(BuiltinType, BuiltinConstFunc):

  PYTHON_TYPE = file
  
  def __init__(self):
    FileType.TYPE = self
    BuiltinConstFunc.__init__(self, 'file', FileType.get_object(),
                              [StrType],
                              [StrType, IntType])
    return
  
  def get_attr(self, name):
    if name == 'close':
      return XXX
    elif name == 'closed':
      return XXX
    elif name == 'encoding':
      return XXX
    elif name == 'fileno':
      return XXX
    elif name == 'flush':
      return XXX
    elif name == 'isatty':
      return XXX
    elif name == 'mode':
      return XXX
    elif name == 'name':
      return XXX
    elif name == 'newlines':
      return XXX
    elif name == 'next':
      return XXX
    elif name == 'read':
      return XXX
    elif name == 'readline':
      return XXX
    elif name == 'readlines':
      return XXX
    elif name == 'seek':
      return XXX
    elif name == 'softspace':
      return XXX
    elif name == 'tell':
      return XXX
    elif name == 'truncate':
      return XXX
    elif name == 'write':
      return XXX
    elif name == 'writelines':
      return XXX
    elif name == 'xreadlines':
      return XXX
    raise NodeAttrError(name)


##  ObjectType
##
class ObjectType(BuiltinType, BuiltinConstFunc):

  PYTHON_TYPE = object
  
  def __init__(self):
    ObjectType.TYPE = self
    BuiltinConstFunc.__init__(self, 'object', ObjectType.get_object())
    return



#
BUILTIN_OBJECTS = dict(
  (cls.get_name(), cls.get_object()) for cls in
  ( NoneType, BoolType, IntType, LongType, FloatType, ComplexType, StrType, UnicodeType )
  )
