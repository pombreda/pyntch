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

  PYTHON_TYPE = type
  RANK = None
  
  def __init__(self):
    SimpleTypeNode.__init__(self, self.__class__)
    return

  @classmethod
  def get_name(klass):
    return klass.PYTHON_TYPE.__name__

  @classmethod
  def get_rank(klass):
    return klass.RANK

  @classmethod
  def get_object(klass):
    return SimpleTypeNode(klass)

  SINGLETON = None
  @classmethod
  def get_type(klass):
    if not klass.SINGLETON:
      klass.SINGLETON = klass()
    return klass.SINGLETON

class BuiltinAggregateType(BuiltinType):
  pass


##  BuiltinFunc
##
class BuiltinFunc(SimpleTypeNode):

  def __init__(self, name, args=None, optargs=None, expts=None):
    SimpleTypeNode.__init__(self, self.__class__)
    args = (args or [])
    optargs = (optargs or [])
    self.name = name
    self.minargs = len(args)
    self.args = args+optargs
    self.expts = (expts or [])
    return

  def __repr__(self):
    return '<builtin %s>' % self.name

  def connect_expt(self, frame):
    return

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
        if obj.is_type(BaseStringType):
          self.parent_frame.raise_expt(ExceptionType(
            'ValueError',
            'might be conversion error'))
        elif obj.is_type((NumberType, BoolType)):
          pass
        else:
          self.parent_frame.raise_expt(ExceptionType(
            'TypeError',
            'cannot convert: %s' % obj))
      return

  def accept_arg(self, caller, i):
    if i == 0:
      return self.IntConversion(caller)
    else:
      return BuiltinConstFunc.accept_arg(self, caller, i)

  def __init__(self):
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
        if obj.is_type(InstanceType):
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
    BuiltinConstFunc.__init__(self, 'unicode', UnicodeType.get_object(),
                              [],
                              [ANY_TYPE])
    return
  

##  Composite Types
##
  
##  ListObject
##
class ListType(BuiltinType, BuiltinFunc):
  
  def process_args(self, caller, args):
    return ListObject(args)

  def __init__(self):
    BuiltinFunc.__init__(self, 'list', [], [ANY_TYPE])
    return
  
class ListObject(BuiltinAggregateType):

  PYTHON_TYPE = ListType
  
  ##  Element
  ##
  class Element(CompoundTypeNode):

    def __init__(self, elements):
      CompoundTypeNode.__init__(self)
      self.elements = elements
      for elem in self.elements:
        elem.connect(self)
      return

    def __repr__(self):
      return '|'.join(map(str, self.elements))

  ##  Methods
  ##
  class AppendMethod(BuiltinConstFunc):
    def __init__(self, listobj):
      self.listobj = listobj
      BuiltinConstFunc.__init__(self, 'list.append', NoneType.get_object(), [ANY_TYPE])
      return
    def __repr__(self):
      return '%r.append' % self.listobj
    def accept_arg(self, caller, _):
      return self.listobj.elem

  class ExtendMethod(BuiltinConstFunc):
    
    class ElementExtender(CompoundTypeNode, ExceptionRaiser):
      def __init__(self, parent_frame, elem, loc):
        self.elem = elem
        CompoundTypeNode.__init__(self)
        ExceptionRaiser.__init__(self, parent_frame, loc)
        return
      def recv(self, src):
        for obj in src.types:
          try:
            obj.get_iter(self).connect(self.elem)
          except NodeTypeError:
            self.raise_expt(ExceptionType(
              'TypeError',
              '%r is not iterable: %r' % (src, obj)))
        return

    def __init__(self, listobj):
      BuiltinConstFunc.__init__(self, 'list.extend', NoneType.get_object(), [ANY_TYPE])
      self.listobj = listobj
      return
    def __repr__(self):
      return '%r.extend' % self.listobj
    def accept_arg(self, caller, i):
      return self.ElementExtender(caller, self.listobj.elem, caller.loc)
    
  class InsertMethod(BuiltinConstFunc):
    def __init__(self, listobj):
      BuiltinConstFunc.__init__(self, 'list.insert', NoneType.get_object(), [IntType, ANY_TYPE], [],
                           [ExceptionType('IndexError', 'might be out of range')])
      self.listobj = listobj
      return
    def __repr__(self):
      return '%r.extend' % self.listobj
    def accept_arg(self, caller, i):
      if i == 0:
        return self.listobj.elem
      else:
        return BuiltinConstFunc.accept_arg(self, caller, i)
      
  class SortMethod(BuiltinConstFunc):
    def __init__(self, listobj):
      BuiltinConstFunc.__init__(self, 'list.sort', NoneType.get_object())
      self.listobj = listobj
      return
    def __repr__(self):
      return '%r.sort' % self.listobj
  #
  def __init__(self, elems):
    BuiltinAggregateType.__init__(self)
    self.elem = self.Element(elems)
    return
  
  def __repr__(self):
    return '[%s]' % self.elem

  def desc1(self, done):
    return '[%s]' % self.elem.desc1(done)

  def bind(self, obj):
    obj.connect(self.elem)
    return

  def get_attr(self, name):
    if name == 'append':
      return self.AppendMethod(self)
    elif name == 'count':
      return BuiltinConstFunc('list.count', IntType.get_object(),
                         [ANY_TYPE])
    elif name == 'extend':
      return self.ExtendMethod(self)
    elif name == 'index':
      return BuiltinConstFunc('list.index', IntType.get_object(),
                         [ANY_TYPE],
                         [IntType, IntType],
                         [ExceptionType('ValueError', 'might not able to find the element')])
    elif name == 'insert':
      return self.InsertMethod(self)
    elif name == 'pop':
      return BuiltinConstFunc('list.pop', NoneType.get_object(),
                         [],
                         [IntType],
                         [ExceptionType('IndexError', 'might be out of range')])
    elif name == 'remove':
      return BuiltinConstFunc('list.remove', NoneType.get_object(),
                         [ANY_TYPE],
                         [ExceptionType('ValueError', 'might not able to remove the element')])
    elif name == 'reverse':
      return BuiltinConstFunc('list.remove', NoneType.get_object())
    elif name == 'sort':
      return self.SortMethod(NoneType.get_object())
    raise NodeAttrError(name)

  def get_element(self, caller, subs, write=False):
    caller.raise_expt(ExceptionType(
      'IndexError',
      '%r index might be out of range.' % self))
    return self.elem

  def get_iter(self, caller):
    return self.elem


##  DictObject
##
class DictType(BuiltinType, BuiltinFunc):
  
  def process_args(self, caller, args):
    return DictObject(args)

  def __init__(self):
    BuiltinFunc.__init__(self, 'dict', [], [ANY_TYPE]) # XXX take keyword argument!
    return

class DictObject(BuiltinAggregateType):

  PYTHON_TYPE = DictType
  
  ##  Item
  class Item(CompoundTypeNode):
    def __init__(self, objs):
      CompoundTypeNode.__init__(self)
      for obj in objs:
        obj.connect(self)
      return

  class SetDefault(BuiltinConstFunc):
    def __init__(self, dictobj):
      self.dictobj = dictobj
      BuiltinConstFunc.__init__(self, 'dict.setdefault', CompoundTypeNode(), [ANY_TYPE], [ANY_TYPE])
      return
    def __repr__(self):
      return '%r.setdefault' % self.dictobj
    def accept_arg(self, caller, i):
      if i == 0:
        return self.dictobj.default
      else:
        return self.retval

  def __init__(self, items):
    self.items = items
    self.default = CompoundTypeNode()
    self.key = self.Item( k for (k,v) in items )
    self.value = self.Item( v for (k,v) in items )
    NoneType.get_object().connect(self.default)
    BuiltinAggregateType.__init__(self)
    return
  
  def __repr__(self):
    return '{%s: %s}' % (self.key, self.value)

  def copy(self):
    return DictObject(self.items)

  def desc1(self, done):
    return '{%s: %s}' % (self.key.desc1(done), self.value.desc1(done))

  def bind(self, key, value):
    key.connect(self.key)
    value.connect(self.value)
    return

  def get_attr(self, name):
    if name == 'clear':
      return BuiltinConstFunc('dict.claer', NoneType.get_object())
    elif name == 'copy':
      return BuiltinConstFunc('dict.copy', self.copy())
    elif name == 'fromkeys':
      return XXX
    elif name == 'get':
      return XXX
    elif name == 'has_key':
      return BuiltinConstFunc('dict.has_key', BoolType.get_object(), [ANY_TYPE])
    elif name == 'items':
      return BuiltinConstFunc('dict.items', ListObject([ TupleObject([self.key, self.value]) ]))
    elif name == 'iteritems':
      return BuiltinConstFunc('dict.iteritems', IterObject([ TupleObject([self.key, self.value]) ]))
    elif name == 'iterkeys':
      return BuiltinConstFunc('dict.iterkeys', IterObject([ TupleObject([self.key]) ]))
    elif name == 'itervalues':
      return BuiltinConstFunc('dict.itervalues', IterObject([ TupleObject([self.value]) ]))
    elif name == 'keys':
      return BuiltinConstFunc('dict.keys', ListObject([ TupleObject([self.key]) ]))
    elif name == 'pop':
      return XXX
      return BuiltinConstFunc('dict.pop', self.value, [ANY_TYPE])
    elif name == 'popitem':
      return BuiltinConstFunc('dict.popitem', TupleObject([self.key, self.value]))
    elif name == 'setdefault':
      return self.SetDefault()
    elif name == 'update':
      return XXX
    elif name == 'values':
      return BuiltinConstFunc('dict.keys', ListObject([ TupleObject([self.key]) ]))
    raise NodeAttrError(name)

  def get_element(self, caller, subs, write=False):
    assert len(subs) == 1
    key = subs[0]
    if write:
      key.connect(self.key)
    else:
      caller.raise_expt(ExceptionType(
        'KeyError',
        'might not have the key: %r' % key))
    return self.value

  def get_iter(self, caller):
    return self.key
  

##  TupleObject
##
class TupleType(BuiltinType, BuiltinFunc):
  
  def process_args(self, caller, args):
    return TupleObject(args)

  def __init__(self):
    BuiltinFunc.__init__(self, 'tuple', [], [ANY_TYPE]) # XXX take keyword argument!
    return

class TupleObject(BuiltinAggregateType):

  PYTHON_TYPE = TupleType
  
  ##  ElementAll
  ##
  class ElementAll(CompoundTypeNode):

    def __init__(self, elements):
      CompoundTypeNode.__init__(self)
      self.elements = elements
      for elem in self.elements:
        elem.connect(self)
      return

    def __repr__(self):
      return '|'.join(map(str, self.elements))

  def __init__(self, elements, loc=None):
    SimpleTypeNode.__init__(self, self.__class__)
    self.elements = elements
    self.loc = loc
    self.elemall = self.ElementAll(elements)
    return
  
  def __repr__(self):
    return '(%s)' % ','.join(map(repr, self.elements))

  def desc1(self, done):
    return '(%s)' % ','.join( elem.desc1(done) for elem in self.elements )

  def get_element(self, caller, subs, write=False):
    if write:
      caller.raise_expt(ExceptionType(
        'TypeError',
        'cannot assign to a tuple.'))
    else:
      caller.raise_expt(ExceptionType(
        'IndexError',
        '%r index might be out of range.' % self))
    return self.elemall

  def get_iter(self, caller):
    return self.elemall
  

##  TupleUnpack
##
class TupleUnpack(CompoundTypeNode, ExceptionRaiser):

  ##  Element
  ##
  class Element(CompoundTypeNode):
    
    def __init__(self, tup, i):
      CompoundTypeNode.__init__(self)
      self.tup = tup
      self.i = i
      return
    
    def __repr__(self):
      return '<TupleElement: %r[%d]>' % (self.tup, self.i)

  def __init__(self, parent_frame, loc, tupobj, nelems):
    CompoundTypeNode.__init__(self)
    self.tupobj = tupobj
    self.elems = [ self.Element(self, i) for i in xrange(nelems) ]
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.tupobj.connect(self, self.recv_tupobj)
    return

  def __repr__(self):
    return '<TupleUnpack: %r>' % (self.tupobj,)

  def get_nth(self, i):
    return self.elems[i]

  def recv_tupobj(self, src):
    assert src is self.tupobj
    for obj in src.types:
      if obj.is_type(TupleObject):
        if len(obj.elements) != len(self.elems):
          self.raise_expt(ExceptionType(
            'ValueError',
            'tuple unpackable: len(%r) != %r' % (obj, len(self.elems))))
        else:
          for (i,elem) in enumerate(obj.elements):
            elem.connect(self.elems[i])
      else:
        try:
          src = obj.get_iter(self)
          for elem in self.elems:
            src.connect(elem)
        except NodeTypeError:
          self.raise_expt(ExceptionType(
            'TypeError',
            'not iterable: %r' % src))
    return


##  IterObject
##
class IterObject(BuiltinAggregateType):

  def __init__(self, yields):
    BuiltinAggregateType.__init__(self)
    self.elem = ListObject.Element(yields)
    return

  def __repr__(self):
    return '(%s, ...)' % self.elem

  def desc1(self, done):
    return '(%s, ...)' % self.elem.desc1(done)

  def get_iter(self, caller):
    return self.elem


##  GeneratorSlot
##
class GeneratorSlot(CompoundTypeNode):

  def __init__(self, value):
    CompoundTypeNode.__init__(self, [self])
    self.value = value
    return


##  SetObject
##
class SetObject(BuiltinAggregateType):

  PYTHON_TYPE = set

  ##  Item
  class Item(CompoundTypeNode):
    def __init__(self, objs):
      CompoundTypeNode.__init__(self)
      for obj in objs:
        obj.connect(self)
      return

  def __init__(self, elems):
    self.elem = CompoundTypeNode()
    for elem in elems:
      elem.connect(self.elem)
    BuiltinAggregateType.__init__(self)
    return
  
  def __repr__(self):
    return '([%s])' % (self.elem)

  def copy(self):
    return SetType([self.elem])

  def get_attr(self, name):
    if name == 'add':
      return XXX
    elif name == 'clear':
      return XXX
    elif name == 'copy':
      return XXX
    elif name == 'difference':
      return XXX
    elif name == 'difference_update':
      return XXX
    elif name == 'discard':
      return XXX
    elif name == 'intersection':
      return XXX
    elif name == 'intersection_update':
      return XXX
    elif name == 'issubset':
      return XXX
    elif name == 'issuperset':
      return XXX
    elif name == 'pop':
      return XXX
    elif name == 'remove':
      return XXX
    elif name == 'symmetric_difference':
      return XXX
    elif name == 'symmetric_difference_update':
      return XXX
    elif name == 'union':
      return XXX
    elif name == 'update':
      return XXX
    raise NodeAttrError(name)

class SetType(BuiltinType, BuiltinFunc):
  
  def process_args(self, caller, args):
    return SetObject(args)

  def __init__(self):
    BuiltinFunc.__init__(self, 'set', [], [ANY_TYPE])
    return
  

##  FileType
##
class FileType(BuiltinType, BuiltinConstFunc):

  PYTHON_TYPE = file
  
  def __init__(self):
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
    BuiltinConstFunc.__init__(self, 'object', ObjectType.get_object())
    return



#
BUILTIN_TYPE = dict(
  (cls.get_name(), cls.get_object()) for cls in
  ( NoneType, BoolType, IntType, LongType, FloatType, StrType, UnicodeType )
  )
