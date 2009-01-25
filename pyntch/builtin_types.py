#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import TypeNode, SimpleTypeNode, CompoundTypeNode, BuiltinType, NodeAttrError, UndefinedTypeNode
from exception import ExceptionRaiser, TypeChecker, ElementTypeChecker
from exception import TypeErrorType, ValueErrorType, IndexErrorType, IOErrorType, EOFErrorType, \
     UnicodeDecodeErrorType, UnicodeEncodeErrorType
from function import KeywordArg, ClassType, InstanceType

ANY_TYPE = False


# ElementAll
class ElementAll(CompoundTypeNode):
  def __init__(self, elements):
    CompoundTypeNode.__init__(self)
    for obj in elements:
      obj.connect(self)
    return


##  BuiltinFunc
##
class BuiltinFunc(BuiltinType):

  def __init__(self, name, args=None, optargs=None, expts=None):
    args = (args or [])
    optargs = (optargs or [])
    self.name = name
    self.minargs = len(args)
    self.args = args+optargs
    self.expts = (expts or [])
    BuiltinType.__init__(self)
    return

  def __repr__(self):
    return '<builtin %s>' % self.name

  @classmethod
  def get_name(klass):
    return 'builtin'
  
  def connect_expt(self, frame):
    return

  def process_args(self, caller, args, kwargs):
    raise NotImplementedError
  
  def call(self, caller, args, kwargs):
    if len(args) < self.minargs:
      caller.raise_expt(TypeErrorType.occur(
        'too few argument for %s: %d or more.' % (self.name, self.minargs)))
      return UndefinedTypeNode()
    if len(self.args) < len(args):
      caller.raise_expt(TypeErrorType.occur(
        'too many argument for %s: at most %d.' % (self.name, len(self.args))))
      return UndefinedTypeNode()
    return self.process_args(caller, args, kwargs)


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

  def process_args(self, caller, args, kwargs):
    if kwargs:
      caller.raise_expt(TypeErrorType.occur(
        'cannot take keyword argument: %r' % arg1.name))
    for (i,arg1) in enumerate(args):
      assert isinstance(arg1, TypeNode)
      rcpt = self.accept_arg(caller, i)
      if rcpt:
        arg1.connect(rcpt)
    for expt in self.expts:
      caller.raise_expt(expt)
    return self.retype

  
##  IterObject
##
class IterType(BuiltinType):

  @classmethod
  def get_name(klass):
    return 'iterator'
  
class IterObject(SimpleTypeNode):

  def __init__(self, elements=None, elemall=None):
    if elements == None:
      assert elemall != None
      self.elemall = elemall
    else:
      assert elements != None
      self.elemall = ElementAll(elements)
    SimpleTypeNode.__init__(self, self)
    return
  
  def __repr__(self):
    return '(%s, ...)' % self.elemall

  def desc1(self, done):
    return '(%s, ...)' % self.elemall.desc1(done)

  @classmethod
  def get_type(klass):
    return IterType.get_type()

  def get_iter(self, caller):
    return self

  def get_attr(self, name, write=False):
    if name == 'next':
      return BuiltinConstFunc('iter.next', self.elemall)
    raise NodeAttrError(name)

##  IterFunc
##
class IterFunc(BuiltinFunc):

  class IterConversion(CompoundTypeNode, ExceptionRaiser):
    
    def __init__(self, parent_frame, loc, obj):
      self.iterobj = IterObject([])
      CompoundTypeNode.__init__(self, [self.iterobj])
      ExceptionRaiser.__init__(self, parent_frame, loc)
      obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_iter(self).connect(self.iterobj.elemall)
        except NodeTypeError:
          self.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
      return self.iterobj
  
  def process_args(self, caller, args):
    return self.IterConversion(caller, caller.loc, args[0])

  def __init__(self):
    BuiltinFunc.__init__(self, 'iter', [ANY_TYPE])
    return
  


##  GeneratorSlot
##
class GeneratorSlot(CompoundTypeNode):

  def __init__(self, value):
    CompoundTypeNode.__init__(self, [self])
    self.value = value
    return


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
      for obj in src:
        if obj.is_type(BaseStringType.get_typeobj()):
          self.parent_frame.raise_expt(ValueErrorType.maybe('might be conversion error.'))
        elif obj.is_type((NumberType.get_typeobj(), BoolType.get_typeobj())):
          pass
        else:
          self.parent_frame.raise_expt(TypeErrorType.occur('cannot convert to integer: %s' % obj))
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

class BaseStringType(BuiltinConstFunc):
  PYTHON_TYPE = basestring

  class JoinFunc(BuiltinConstFunc):
    def accept_arg(self, caller, i):
      return ElementTypeChecker(caller, self.args[i].get_type(), caller.loc, 'arg%d' % i)

  def get_attr(self, name, write=False):
    from aggregate_types import TupleObject, ListObject
    if name == 'capitalize':
      return BuiltinConstFunc('str.capitalize',
                              self.get_object())
    elif name == 'center':
      return BuiltinConstFunc('str.center',
                              self.get_object(),
                              [IntType], 
                              [BaseStringType])
    elif name == 'count':
      return BuiltinConstFunc('str.count',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'decode':
      return BuiltinConstFunc('str.decode',
                              UnicodeType.get_object(),
                              [],
                              [BaseStringType, BaseStringType],
                              [UnicodeDecodeErrorType.maybe('might not able to decode.')])
    elif name == 'encode':
      return BuiltinConstFunc('str.encode',
                              StrType.get_object(),
                              [],
                              [BaseStringType, BaseStringType],
                              [UnicodeDecodeErrorType.maybe('might not able to encode.')])
    elif name == 'endswith':
      return BuiltinConstFunc('str.endswith',
                              BoolType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'expandtabs':
      return BuiltinConstFunc('str.expandtabs',
                              self.get_object(),
                              [],
                              [IntType])
    elif name == 'find':
      return BuiltinConstFunc('str.find',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'index':
      return BuiltinConstFunc('str.index',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType],
                              [ValueErrorType.maybe('might not able to find the substring.')])
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
      return BuiltinConstFunc('str.partiion',
                              TupleObject([self.get_object(), self.get_object(), self.get_object()]),
                              [BaseStringType])
    elif name == 'replace':
      return BuiltinConstFunc('str.replace',
                              self.get_object(),
                              [BaseStringType, BaseStringType], [IntType])
    elif name == 'rfind':
      return BuiltinConstFunc('str.rfind',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'rindex':
      return BuiltinConstFunc('str.rindex',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType],
                              [ValueErrorType.maybe('might not able to find the substring.')])
    elif name == 'rjust':
      return BuiltinConstFunc('str.rjust',
                              self.get_object(),
                              [IntType], 
                              [BaseStringType])
    elif name == 'rpartition':
      return BuiltinConstFunc('str.rpartiion',
                              TupleObject([self.get_object(), self.get_object(), self.get_object()]),
                              [BaseStringType])
    elif name == 'rsplit':
      return BuiltinConstFunc('str.rsplit',
                              ListObject([self.get_object()]),
                              [],
                              [BaseStringType, IntType])
    elif name == 'rstrip':
      return BuiltinConstFunc('str.rstrip',
                              self.get_object(),
                              [BaseStringType])
    elif name == 'split':
      return BuiltinConstFunc('str.split',
                              ListObject([self.get_object()]),
                              [],
                              [BaseStringType, IntType])
    elif name == 'splitlines':
      return BuiltinConstFunc('str.splitlines',
                              ListObject([self.get_object()]),
                              [],
                              [ANY_TYPE])
    elif name == 'startswith':
      return BuiltinConstFunc('str.startswith',
                              BoolType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'strip':
      return BuiltinConstFunc('str.strip',
                              self.get_object(),
                              [BaseStringType])
    elif name == 'swapcase':
      return BuiltinConstFunc('str.swapcase',
                              self.get_object())
    elif name == 'title':
      return BuiltinConstFunc('str.title',
                              self.get_object())
    elif name == 'upper':
      return BuiltinConstFunc('str.upper',
                              self.get_object())
    elif name == 'zfill':
      return BuiltinConstFunc('str.zfill',
                              self.get_object(),
                              [IntType])
    raise NodeAttrError(name)

  def get_iter(self, caller):
    return IterObject(elemall=self.get_object())

  def get_element(self, caller, subs, write=False):
    if write:
      caller.raise_expt(TypeErrorType.occur('cannot change a string.'))
    else:
      caller.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self.get_object()

  class StrConversion(CompoundTypeNode, ExceptionRaiser):
    
    def __init__(self, parent_frame, loc):
      CompoundTypeNode.__init__(self)
      ExceptionRaiser.__init__(self, parent_frame, loc)
      return
    
    def recv(self, src):
      for obj in src:
        if isinstance(obj, InstanceType):
          value = ClassType.OptionalAttr(obj, '__str__').call(self, (), {})
          value.connect(TypeChecker(self, BaseStringType.get_typeobj(), self.loc,
                                    'the return value of __str__ method'))
          value = ClassType.OptionalAttr(obj, '__repr__').call(self, (), {})
          value.connect(TypeChecker(self, BaseStringType.get_typeobj(), self.loc,
                                    'the return value of __repr__ method'))
      return

  def accept_arg(self, caller, _):
    return self.StrConversion(caller, caller.loc)

  def call(self, caller, args, kwargs):
    if self.PYTHON_TYPE is basestring:
      caller.raise_expt(TypeErrorType.occur('cannot instantiate a basestring type.'))
      return UndefinedTypeNode()
    return BuiltinConstFunc.call(self, caller, args, kwargs)
  
  def __init__(self):
    BuiltinConstFunc.__init__(self, 'basestring', None)
    return
  
class StrType(BaseStringType):
  PYTHON_TYPE = str
  
  def get_attr(self, name, write=False):
    if name == 'translate':
      return BuiltinConstFunc('str.translate', self.get_object(),
                              [BaseStringType],
                              [BaseStringType],
                              [ValueErrorType.maybe('table might not be 256 chars long.')])
    return BaseStringType.get_attr(self, name, write=write)
    
  def __init__(self):
    StrType.TYPE = self
    BuiltinConstFunc.__init__(self, 'str', StrType.get_object(),
                              [],
                              [ANY_TYPE])
    return
  
class UnicodeType(BaseStringType):
  PYTHON_TYPE = unicode

  def get_attr(self, name, write=False):
    if name == 'isdecimal':
      return BuiltinConstFunc('unicode.isdecimal',
                              BoolType.get_object())
    elif name == 'isnumeric':
      return BuiltinConstFunc('unicode.isnumeric',
                              BoolType.get_object())
    elif name == 'translate':
      return XXX
      return BuiltinConstFunc('unicode.translate',
                              self.get_object(),
                              [BaseStringType])
    return BaseStringType.get_attr(self, name, write=write)

  def __init__(self):
    UnicodeType.TYPE = self
    BuiltinConstFunc.__init__(self, 'unicode',
                              UnicodeType.get_object(),
                              [],
                              [ANY_TYPE])
    return
  

##  FileType
##
class FileType(BuiltinConstFunc):

  PYTHON_TYPE = file
  
  def __init__(self):
    FileType.TYPE = self
    BuiltinConstFunc.__init__(self, 'file',
                              FileType.get_object(),
                              [StrType],
                              [StrType, IntType],
                              [IOErrorType.maybe('might not able to open a file.')])
    return
  
  def get_attr(self, name, write=False):
    if name == 'close':
      return BuiltinConstFunc('file.close',
                              NoneType.get_object())
    elif name == 'closed':
      return BoolType.get_object()
    elif name == 'encoding':
      return StrType.get_object()
    elif name == 'fileno':
      return BuiltinConstFunc('file.fileno',
                              IntType.get_object())
    elif name == 'flush':
      return BuiltinConstFunc('file.flush',
                              NoneType.get_object())
    elif name == 'isatty':
      return BuiltinConstFunc('file.isatty',
                              BoolType.get_object())
    elif name == 'mode':
      return StrType.get_object()
    elif name == 'name':
      return StrType.get_object()
    elif name == 'newlines':
      return NoneType.get_object()
    elif name == 'next':
      return BuiltinConstFunc('file.next',
                              StrType.get_object())
    elif name == 'read':
      return BuiltinConstFunc('file.read',
                              StrType.get_object(),
                              [],
                              [IntType],
                              [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'readline':
      return BuiltinConstFunc('file.readline',
                              StrType.get_object(),
                              [],
                              [IntType],
                              [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'readlines':
      return BuiltinConstFunc('file.readlines',
                              ListObject([StrType.get_object()]),
                              [],
                              [IntType],
                              [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'seek':
      return BuiltinConstFunc('file.seek',
                              NoneType.get_object(),
                              [IntType],
                              [IntType],
                              [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'softspace':
      return IntType.get_object()
    elif name == 'tell':
      return BuiltinConstFunc('file.tell',
                              IntType.get_object(),
                              [],
                              [],
                              [IOErrorType.maybe('might be an illegal seek.')])
    elif name == 'truncate':
      return BuiltinConstFunc('file.truncate',
                              NoneType.get_object(),
                              [],
                              [IntType])
    elif name == 'write':
      return BuiltinConstFunc('file.write',
                              NoneType.get_object(),
                              [StrType])
    elif name == 'writelines':
      return XXX
    elif name == 'xreadlines':
      return self
    raise NodeAttrError(name)

  def get_iter(self, caller):
    return IterObject(elemall=StrType.get_object())


##  ObjectType
##
class ObjectType(BuiltinConstFunc):

  PYTHON_TYPE = object
  
  def __init__(self):
    ObjectType.TYPE = self
    BuiltinConstFunc.__init__(self, 'object', ObjectType.get_object())
    return

##  TypeType
##
class TypeType(BuiltinType):
  PYTHON_TYPE = type



#
BUILTIN_OBJECTS = dict(
  (cls.get_name(), cls.get_object()) for cls in
  ( NoneType, BoolType, IntType, LongType, FloatType, ComplexType, StrType, UnicodeType )
  )
