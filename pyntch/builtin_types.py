#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import TypeNode, SimpleTypeNode, CompoundTypeNode, BuiltinType, NodeAttrError, UndefinedTypeNode
from exception import TypeChecker, ElementTypeChecker
from exception import TypeErrorType, ValueErrorType, IndexErrorType, IOErrorType, EOFErrorType, \
     UnicodeDecodeErrorType, UnicodeEncodeErrorType
from function import ClassType, InstanceType

ANY_TYPE = False


# ElementAll
class ElementAll(CompoundTypeNode):
  def __init__(self, elements):
    CompoundTypeNode.__init__(self)
    for obj in elements:
      obj.connect(self)
    return


##  InternalFunc
##
class InternalFunc(SimpleTypeNode):

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
    return '<internal %s>' % self.name
  
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


##  InternalConstFunc
##
class InternalConstFunc(InternalFunc):
  
  def __init__(self, name, retype, args=None, optargs=None, expts=None):
    self.retype = retype
    InternalFunc.__init__(self, name, args=args, optargs=optargs, expts=expts)
    return

  def accept_arg(self, frame, i):
    if self.args[i]:
      return TypeChecker(frame, self.args[i].get_type(), 'arg%d' % i)
    else:
      return None

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur(
        'cannot take keyword argument: %r' % arg1.name))
    for (i,arg1) in enumerate(args):
      assert isinstance(arg1, TypeNode)
      rcpt = self.accept_arg(frame, i)
      if rcpt:
        arg1.connect(rcpt)
    for expt in self.expts:
      frame.raise_expt(expt)
    return self.retype


class BuiltinFunc(InternalFunc, BuiltinType):
  def __init__(self, name, args=None, optargs=None, expts=None):
    InternalFunc.__init__(self, name, args=args, optargs=optargs, expts=expts)
    BuiltinType.__init__(self)
    return
  def __repr__(self):
    return '<builtin %s>' % self.name
  @classmethod
  def get_name(self):
    return 'builtin'

class BuiltinConstFunc(InternalConstFunc, BuiltinType):
  def __init__(self, name, retype, args=None, optargs=None, expts=None):
    InternalConstFunc.__init__(self, name, retype, args=args, optargs=optargs, expts=expts)
    BuiltinType.__init__(self)
    return
  def __repr__(self):
    return '<builtin %s>' % self.name
  @classmethod
  def get_name(self):
    return 'builtin'


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

  def get_iter(self, frame):
    return self

  def get_attr(self, name, write=False):
    if name == 'next':
      return InternalConstFunc('iter.next', self.elemall)
    raise NodeAttrError(name)

##  IterFunc
##
class IterFunc(BuiltinFunc):

  class IterConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.iterobj = IterObject([])
      CompoundTypeNode.__init__(self, [self.iterobj])
      obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_iter(self).connect(self.iterobj.elemall)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
      return self.iterobj
  
  def process_args(self, frame, args):
    return self.IterConversion(frame, args[0])

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
  
class IntType(NumberType, InternalConstFunc):
  PYTHON_TYPE = int
  RANK = 1

  class IntConversion(CompoundTypeNode):
    
    def __init__(self, frame):
      self.frame = frame
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      for obj in src:
        if obj.is_type(BaseStringType.get_typeobj()):
          self.frame.raise_expt(ValueErrorType.maybe('might be conversion error.'))
        elif obj.is_type((NumberType.get_typeobj(), BoolType.get_typeobj())):
          pass
        else:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to integer: %s' % obj))
      return

  def accept_arg(self, frame, i):
    if i == 0:
      return self.IntConversion(frame)
    else:
      return InternalConstFunc.accept_arg(self, frame, i)

  def __init__(self):
    IntType.TYPE = self
    BuiltinType.__init__(self)
    InternalConstFunc.__init__(self, 'int', IntType.get_object(),
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

class BaseStringType(BuiltinType, InternalConstFunc):
  PYTHON_TYPE = basestring

  class JoinFunc(InternalConstFunc):
    def accept_arg(self, frame, i):
      return ElementTypeChecker(frame, self.args[i].get_type(), 'arg%d' % i)

  def get_attr(self, name, write=False):
    from aggregate_types import TupleObject, ListObject
    if name == 'capitalize':
      return InternalConstFunc('str.capitalize',
                              self.get_object())
    elif name == 'center':
      return InternalConstFunc('str.center',
                              self.get_object(),
                              [IntType], 
                              [BaseStringType])
    elif name == 'count':
      return InternalConstFunc('str.count',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'decode':
      return InternalConstFunc('str.decode',
                              UnicodeType.get_object(),
                              [],
                              [BaseStringType, BaseStringType],
                              [UnicodeDecodeErrorType.maybe('might not able to decode.')])
    elif name == 'encode':
      return InternalConstFunc('str.encode',
                              StrType.get_object(),
                              [],
                              [BaseStringType, BaseStringType],
                              [UnicodeDecodeErrorType.maybe('might not able to encode.')])
    elif name == 'endswith':
      return InternalConstFunc('str.endswith',
                              BoolType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'expandtabs':
      return InternalConstFunc('str.expandtabs',
                              self.get_object(),
                              [],
                              [IntType])
    elif name == 'find':
      return InternalConstFunc('str.find',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'index':
      return InternalConstFunc('str.index',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType],
                              [ValueErrorType.maybe('might not able to find the substring.')])
    elif name == 'isalnum':
      return InternalConstFunc('str.isalnum', BoolType.get_object())
    elif name == 'isalpha':
      return InternalConstFunc('str.isalpha', BoolType.get_object())
    elif name == 'isdigit':
      return InternalConstFunc('str.isdigit', BoolType.get_object())
    elif name == 'islower':
      return InternalConstFunc('str.islower', BoolType.get_object())
    elif name == 'isspace':
      return InternalConstFunc('str.isspace', BoolType.get_object())
    elif name == 'istitle':
      return InternalConstFunc('str.istitle', BoolType.get_object())
    elif name == 'isupper':
      return InternalConstFunc('str.isupper', BoolType.get_object())
    elif name == 'join':
      return self.JoinFunc('str.join', self.get_object(),
                           [BaseStringType])
    elif name == 'ljust':
      return InternalConstFunc('str.ljust', self.get_object(),
                              [IntType], 
                              [BaseStringType])
    elif name == 'lower':
      return InternalConstFunc('str.lower', self.get_object())
    elif name == 'lstrip':
      return InternalConstFunc('str.lstrip', self.get_object(),
                              [BaseStringType])
    elif name == 'partition':
      return InternalConstFunc('str.partiion',
                              TupleObject([self.get_object(), self.get_object(), self.get_object()]),
                              [BaseStringType])
    elif name == 'replace':
      return InternalConstFunc('str.replace',
                              self.get_object(),
                              [BaseStringType, BaseStringType], [IntType])
    elif name == 'rfind':
      return InternalConstFunc('str.rfind',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'rindex':
      return InternalConstFunc('str.rindex',
                              IntType.get_object(),
                              [BaseStringType],
                              [IntType, IntType],
                              [ValueErrorType.maybe('might not able to find the substring.')])
    elif name == 'rjust':
      return InternalConstFunc('str.rjust',
                              self.get_object(),
                              [IntType], 
                              [BaseStringType])
    elif name == 'rpartition':
      return InternalConstFunc('str.rpartiion',
                              TupleObject([self.get_object(), self.get_object(), self.get_object()]),
                              [BaseStringType])
    elif name == 'rsplit':
      return InternalConstFunc('str.rsplit',
                              ListObject([self.get_object()]),
                              [],
                              [BaseStringType, IntType])
    elif name == 'rstrip':
      return InternalConstFunc('str.rstrip',
                              self.get_object(),
                              [BaseStringType])
    elif name == 'split':
      return InternalConstFunc('str.split',
                              ListObject([self.get_object()]),
                              [],
                              [BaseStringType, IntType])
    elif name == 'splitlines':
      return InternalConstFunc('str.splitlines',
                              ListObject([self.get_object()]),
                              [],
                              [ANY_TYPE])
    elif name == 'startswith':
      return InternalConstFunc('str.startswith',
                              BoolType.get_object(),
                              [BaseStringType],
                              [IntType, IntType])
    elif name == 'strip':
      return InternalConstFunc('str.strip',
                              self.get_object(),
                              [BaseStringType])
    elif name == 'swapcase':
      return InternalConstFunc('str.swapcase',
                              self.get_object())
    elif name == 'title':
      return InternalConstFunc('str.title',
                              self.get_object())
    elif name == 'upper':
      return InternalConstFunc('str.upper',
                              self.get_object())
    elif name == 'zfill':
      return InternalConstFunc('str.zfill',
                              self.get_object(),
                              [IntType])
    raise NodeAttrError(name)

  def get_iter(self, frame):
    return IterObject(elemall=self.get_object())

  def get_element(self, frame, subs, write=False):
    if write:
      frame.raise_expt(TypeErrorType.occur('cannot change a string.'))
    else:
      frame.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self.get_object()

  class StrConversion(CompoundTypeNode):
    
    def __init__(self, frame):
      self.frame = frame
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      for obj in src:
        if isinstance(obj, InstanceType):
          value = ClassType.OptionalAttr(obj, '__str__').call(self.frame, (), {})
          value.connect(TypeChecker(self.frame, BaseStringType.get_typeobj(), 
                                    'the return value of __str__ method'))
          value = ClassType.OptionalAttr(obj, '__repr__').call(self.frame, (), {})
          value.connect(TypeChecker(self.frame, BaseStringType.get_typeobj(), 
                                    'the return value of __repr__ method'))
      return

  def accept_arg(self, frame, _):
    return self.StrConversion(frame)

  def call(self, frame, args, kwargs):
    if self.PYTHON_TYPE is basestring:
      frame.raise_expt(TypeErrorType.occur('cannot instantiate a basestring type.'))
      return UndefinedTypeNode()
    return InternalConstFunc.call(self, frame, args, kwargs)
  
  def __init__(self):
    BuiltinType.__init__(self)
    InternalConstFunc.__init__(self, 'basestring', None)
    return
  
class StrType(BaseStringType):
  PYTHON_TYPE = str
  
  def get_attr(self, name, write=False):
    if name == 'translate':
      return InternalConstFunc('str.translate', self.get_object(),
                              [BaseStringType],
                              [BaseStringType],
                              [ValueErrorType.maybe('table might not be 256 chars long.')])
    return BaseStringType.get_attr(self, name, write=write)
    
  def __init__(self):
    StrType.TYPE = self
    BuiltinType.__init__(self)
    InternalConstFunc.__init__(self, 'str', StrType.get_object(),
                              [],
                              [ANY_TYPE])
    return
  
class UnicodeType(BaseStringType):
  PYTHON_TYPE = unicode

  def get_attr(self, name, write=False):
    if name == 'isdecimal':
      return InternalConstFunc('unicode.isdecimal',
                              BoolType.get_object())
    elif name == 'isnumeric':
      return InternalConstFunc('unicode.isnumeric',
                              BoolType.get_object())
    elif name == 'translate':
      return XXX
      return InternalConstFunc('unicode.translate',
                              self.get_object(),
                              [BaseStringType])
    return BaseStringType.get_attr(self, name, write=write)

  def __init__(self):
    UnicodeType.TYPE = self
    BuiltinType.__init__(self)
    InternalConstFunc.__init__(self, 'unicode',
                              UnicodeType.get_object(),
                              [],
                              [ANY_TYPE])
    return
  

##  FileType
##
class FileType(BuiltinType, InternalConstFunc):

  PYTHON_TYPE = file
  
  def __init__(self):
    FileType.TYPE = self
    BuiltinType.__init__(self)
    InternalConstFunc.__init__(self, 'file',
                              FileType.get_object(),
                              [StrType],
                              [StrType, IntType],
                              [IOErrorType.maybe('might not able to open a file.')])
    return
  
  def get_attr(self, name, write=False):
    if name == 'close':
      return InternalConstFunc('file.close',
                              NoneType.get_object())
    elif name == 'closed':
      return BoolType.get_object()
    elif name == 'encoding':
      return StrType.get_object()
    elif name == 'fileno':
      return InternalConstFunc('file.fileno',
                              IntType.get_object())
    elif name == 'flush':
      return InternalConstFunc('file.flush',
                              NoneType.get_object())
    elif name == 'isatty':
      return InternalConstFunc('file.isatty',
                              BoolType.get_object())
    elif name == 'mode':
      return StrType.get_object()
    elif name == 'name':
      return StrType.get_object()
    elif name == 'newlines':
      return NoneType.get_object()
    elif name == 'next':
      return InternalConstFunc('file.next',
                              StrType.get_object())
    elif name == 'read':
      return InternalConstFunc('file.read',
                              StrType.get_object(),
                              [],
                              [IntType],
                              [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'readline':
      return InternalConstFunc('file.readline',
                              StrType.get_object(),
                              [],
                              [IntType],
                              [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'readlines':
      return InternalConstFunc('file.readlines',
                              ListObject([StrType.get_object()]),
                              [],
                              [IntType],
                              [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'seek':
      return InternalConstFunc('file.seek',
                              NoneType.get_object(),
                              [IntType],
                              [IntType],
                              [EOFErrorType.maybe('might receive an EOF.')])
    elif name == 'softspace':
      return IntType.get_object()
    elif name == 'tell':
      return InternalConstFunc('file.tell',
                              IntType.get_object(),
                              [],
                              [],
                              [IOErrorType.maybe('might be an illegal seek.')])
    elif name == 'truncate':
      return InternalConstFunc('file.truncate',
                              NoneType.get_object(),
                              [],
                              [IntType])
    elif name == 'write':
      return InternalConstFunc('file.write',
                              NoneType.get_object(),
                              [StrType])
    elif name == 'writelines':
      return XXX
    elif name == 'xreadlines':
      return self
    raise NodeAttrError(name)

  def get_iter(self, frame):
    return IterObject(elemall=StrType.get_object())


##  ObjectType
##
class ObjectType(BuiltinType, InternalConstFunc):

  PYTHON_TYPE = object
  
  def __init__(self):
    ObjectType.TYPE = self
    BuiltinType.__init__(self)
    InternalConstFunc.__init__(self, 'object', ObjectType.get_object())
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

