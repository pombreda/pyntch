#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import TypeNode, CompoundTypeNode, NodeAttrError, NodeAssignError, \
     BuiltinType, BuiltinBasicType, BuiltinObject, UndefinedTypeNode
from exception import TypeChecker, SequenceTypeChecker
from config import ErrorConfig
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
  
  def call(self, frame, args, kwargs, star, dstar):
    if len(args) < self.minargs:
      frame.raise_expt(ErrorConfig.InvalidNumOfArgs(self.minargs, len(args)))
      return UndefinedTypeNode()
    if len(self.args) < len(args):
      frame.raise_expt(ErrorConfig.InvalidNumOfArgs(len(self.args), len(args)))
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
      frame.raise_expt(ErrorCofnig.NoKeywordArgs())
    for (i,arg1) in enumerate(args):
      assert isinstance(arg1, TypeNode)
      self.accept_arg(frame, i, arg1)
    for expt in self.expts:
      frame.raise_expt(expt)
    return self.retobj

  def accept_arg(self, frame, i, arg1):
    s = 'arg %d' % i
    spec = self.args[i]
    if isinstance(spec, list):
      if spec == [ANY]:
        checker = SequenceTypeChecker(frame, ANY, s)
      else:
        checker = SequenceTypeChecker(frame, [ x.get_typeobj() for x in spec ], s)
    elif isinstance(spec, tuple):
      checker = TypeChecker(frame, [ x.get_typeobj() for x in spec ], s)
    elif spec == ANY:
      checker = TypeChecker(frame, ANY, s)
    else:
      checker = TypeChecker(frame, [spec.get_typeobj()], s)
    arg1.connect(checker.recv)
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
class TypeType(BuiltinConstCallable, BuiltinType):
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
class IntType(BuiltinConstCallable, NumberType):
  TYPE_NAME = 'int'
  TYPE_INSTANCE = IntObject
  RANK = 1

  class IntConverter(CompoundTypeNode):
    
    def __init__(self, frame, value):
      self.frame = frame
      self.done = set()
      CompoundTypeNode.__init__(self, [value])
      return
    
    def recv(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        if obj.is_type(BaseStringType.get_typeobj()):
          self.frame.raise_expt(ErrorConfig.MaybeNotConvertable('int'))
        elif obj.is_type(NumberType.get_typeobj(), BoolType.get_typeobj()):
          pass
        else:
          self.frame.raise_expt(ErrorConfig.NotConvertable('int'))
      return

  def accept_arg(self, frame, i, arg1):
    if i == 0:
      IntType.IntConverter(frame, arg1)
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

  def get_element(self, frame, sub, write=False):
    if write: raise NodeAssignError
    frame.raise_expt(ErrorConfig.MaybeOutOfRange())
    return self

  def get_slice(self, frame, subs, write=False):
    if write: raise NodeAssignError
    frame.raise_expt(ErrorConfig.MaybeOutOfRange())
    return self

class BaseStringType(BuiltinConstCallable, BuiltinBasicType):
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
                                [ErrorConfig.MaybeNotDecodable()])
    elif name == 'encode':
      return BuiltinConstMethod('str.encode', StrType.get_object(),
                                [], [BaseStringType, BaseStringType],
                                [ErrorConfig.MaybeNotEncodable()])
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
                                [ErrorConfig.MaybeSubstringNotFound()])
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
                                [ErrorConfig.MaybeSubstringNotFound()])
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

  class StrConverter(CompoundTypeNode):
    
    def __init__(self, frame, value):
      self.frame = frame
      self.done = set()
      CompoundTypeNode.__init__(self, [value])
      return
    
    def recv(self, src):
      from expression import MethodCall
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        if isinstance(obj, InstanceObject):
          value = MethodCall(self.frame, obj, '__str__')
          checker = TypeChecker(self.frame, BaseStringType.get_typeobj(), 
                                'the return value of __str__ method')
          value.connect(checker.recv)
          value = MethodCall(self.frame, obj, '__repr__')
          checker = TypeChecker(self.frame, BaseStringType.get_typeobj(), 
                                'the return value of __repr__ method')
          value.connect(checker.recv)
      return

  def accept_arg(self, frame, i, arg1):
    self.StrConverter(frame, arg1)
    return

  def call(self, frame, args, kwargs, star, dstar):
    if self.TYPE_NAME == 'basestring':
      frame.raise_expt(ErrorConfig.NotInstantiatable('basestring'))
      return UndefinedTypeNode()
    return BuiltinConstCallable.call(self, frame, args, kwargs, star, dstar)

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
                                [ErrorConfig.MaybeTableInvalid()])
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
      checker = KeyValueTypeChecker(frame, [IntType.get_typeobj()],
                                    [IntType.get_typeobj(), UnicodeType.get_typeobj(), NoneType.get_typeobj()],
                                    'arg %d' % i)
      arg1.connect(checker.recv)
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
  
class FileType(BuiltinConstCallable, BuiltinBasicType):
  TYPE_NAME = 'file'
  TYPE_INSTANCE = FileObject
  
  def __init__(self):
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'file', self.get_object(),
                                  [StrType], [StrType, IntType],
                                  [ErrorConfig.MaybeFileCannotOpen()])
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
                                [ErrorConfig.MaybeEOFError()])
    elif name == 'readline':
      return BuiltinConstMethod('file.readline', StrType.get_object(),
                                [], [IntType],
                                [ErrorConfig.MaybeEOFError()])
    elif name == 'readlines':
      return BuiltinConstMethod('file.readlines', ListType.create_list(StrType.get_object()),
                                [], [IntType],
                                [ErrorConfig.MaybeEOFError()])
    elif name == 'seek':
      return BuiltinConstMethod('file.seek', NoneType.get_object(),
                                [IntType], [IntType],
                                [ErrorConfig.MaybeEOFError()])
    elif name == 'softspace':
      return IntType.get_object()
    elif name == 'tell':
      return BuiltinConstMethod('file.tell', IntType.get_object(),
                                expts=[ErrorConfig.MaybeFileIllegalSeek()])
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
class ObjectType(BuiltinConstCallable, BuiltinBasicType):
  TYPE_NAME = 'object'
  TYPE_INSTANCE = ObjectObject
  
  def __init__(self):
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'object', self.get_object())
    return

BUILTIN_OBJECT = dict(
  (cls.get_name(), cls.get_object()) for cls in
  ( NoneType, BoolType, IntType, LongType, FloatType, ComplexType, StrType, UnicodeType, FileType ))


##  XRangeType
##
class XRangeObject(BuiltinObject):
  
  def __init__(self, typeobj):
    self.iter = None
    BuiltinObject.__init__(self, typeobj)
    return
  
  def get_iter(self, frame):
    from aggregate_types import IterType
    if not self.iter:
      self.iter = IterType.create_iter(IntType.get_object())
    return self.iter

class XRangeType(BuiltinConstCallable, BuiltinBasicType):
  TYPE_NAME = 'xrange'
  TYPE_INSTANCE = XRangeObject
  
  def __init__(self):
    BuiltinBasicType.__init__(self)
    BuiltinConstCallable.__init__(self, 'xrange', self.get_object(),
                                  [IntType], [IntType, IntType])
    return


##  StaticMethodType
##
class StaticMethodObject(BuiltinObject):
  
  def __init__(self, typeobj, realobj):
    self.typeobj = typeobj
    self.realobj = realobj
    BuiltinObject.__init__(self, typeobj)
    return

  def get_object(self):
    return self.realobj

class ClassMethodObject(BuiltinObject):
  
  def __init__(self, typeobj, realobj):
    self.typeobj = typeobj
    self.realobj = realobj
    BuiltinObject.__init__(self, typeobj)
    return

  def get_object(self):
    return self.realobj

class StaticMethodType(BuiltinCallable, BuiltinType):

  class MethodConverter(CompoundTypeNode):

    def __init__(self, typeobj, wrapper, obj):
      self.typeobj = typeobj
      self.wrapper = wrapper
      self.done = set()
      CompoundTypeNode.__init__(self, [obj])
      return
    
    def recv(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        self.update_type(self.wrapper(self.typeobj, obj))
      return

  def __init__(self, name='staticmethod', wrapper=StaticMethodObject):
    self.wrapper = wrapper
    BuiltinType.__init__(self)
    BuiltinCallable.__init__(self, name, [ANY])
    return

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(ErrorConfig.NoKeywordArgs())
      return UndefinedTypeNode()
    return self.MethodConverter(self.get_typeobj(), self.wrapper, args[0])

class ClassMethodType(StaticMethodType):

  def __init__(self):
    StaticMethodType.__init__(self, 'classmethod', wrapper=ClassMethodObject)
    return
