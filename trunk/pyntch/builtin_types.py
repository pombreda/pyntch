#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import TypeNode, SimpleTypeNode, CompoundTypeNode, NodeTypeError
from exception import ExceptionType, ExceptionRaiser, TypeChecker, ElementTypeChecker
from function import KeywordArg


##  BuiltinType
##
class BuiltinType(SimpleTypeNode):

  NAME = None
  SINGLETON = None

  def __repr__(self):
    return '<%s>' % self.NAME

  @classmethod
  def get(klass):
    if not klass.SINGLETON:
      klass.SINGLETON = klass()
    return klass.SINGLETON


class BuiltinAggregateType(BuiltinType):
  pass


##  BuiltinFunc
##
class BuiltinFunc(SimpleTypeNode):

  def __init__(self, name, retval, args=None, optargs=None, expts=None):
    SimpleTypeNode.__init__(self)
    args = (args or [])
    optargs = (optargs or [])
    self.name = name
    self.retval = retval
    self.minargs = len(args)
    self.args = args+optargs
    self.expts = (expts or [])
    return

  def __repr__(self):
    return '<builtin %s>' % self.NAME

  def connect_expt(self, frame):
    return

  def check_arg(self, caller, i):
    return TypeChecker(caller, self.args[i], 'arg%d' % i)

  def call(self, caller, args):
    if len(args) < self.minargs:
      caller.raise_expt(ExceptionType(
        'TypeError',
        'too few argument: %d (at least %d)' % (len(args), self.minargs)))
    elif len(self.args) < len(args):
      caller.raise_expt(ExceptionType(
        'TypeError',
        'too many argument: %d (at most %d)' % (len(args), len(self.args))))
    else:
      for (i,arg1) in enumerate(args):
        if isinstance(arg1, KeywordArg):
          caller.raise_expt(ExceptionType(
            'TypeError',
            'cannot take keyword argument: %r' % arg1.name))
        elif self.args[i]:
          assert isinstance(arg1, TypeNode)
          arg1.connect(self.check_arg(caller, i))
    for expt in self.expts:
      caller.raise_expt(expt)
    return self.retval


##  NoneType
##
class NoneType(BuiltinType):
  NAME = 'NoneType'

class BoolType(BuiltinType):
  NAME = 'bool'

class NumberType(BuiltinType):
  NAME = 'number'
  rank = 0
class IntType(NumberType):
  NAME = 'int'
  rank = 1
class LongType(IntType):
  NAME = 'long'
  rank = 2
class FloatType(NumberType):
  NAME = 'float'
  rank = 3
class ComplexType(NumberType):
  NAME = 'complex'
  rank = 4

class BaseStringType(BuiltinType):
  NAME = 'basestring'

  class JoinFunc(BuiltinFunc):
    def check_arg(self, caller, i):
      return ElementTypeChecker(caller, self.args[i], 'arg%d' % i)

  def get_attr(self, name):
    if name == 'capitalize':
      return BuiltinFunc('str.capitalize', self.get())
    elif name == 'center':
      return BuiltinFunc('str.center', self.get(),
                         [INT_ARG], 
                         [STR_ARG])
    elif name == 'count':
      return BuiltinFunc('str.count', IntType.get(),
                         [STR_ARG],
                         [INT_ARG, INT_ARG])
    elif name == 'decode':
      return BuiltinFunc('str.decode', UnicodeType.get(),
                         [],
                         [STR_ARG, STR_ARG],
                         [ExceptionType('UnicodeDecodeError', 'might not able to decode')])
    elif name == 'encode':
      return BuiltinFunc('str.encode', StrType.get(),
                         [],
                         [STR_ARG, STR_ARG],
                         [ExceptionType('UnicodeEncodeError', 'might not able to encode')])
    elif name == 'endswith':
      return BuiltinFunc('str.endswith', BoolType.get(),
                         [STR_ARG],
                         [INT_ARG, INT_ARG])
    elif name == 'expandtabs':
      return BuiltinFunc('str.expandtabs', self.get(),
                         [],
                         [INT_ARG])
    elif name == 'find':
      return BuiltinFunc('str.find', IntType.get(),
                         [STR_ARG],
                         [INT_ARG, INT_ARG])
    elif name == 'index':
      return BuiltinFunc('str.index', IntType.get(),
                         [STR_ARG],
                         [INT_ARG, INT_ARG],
                         [ExceptionType('ValueError', 'might not able to find the substring')])             
    elif name == 'isalnum':
      return BuiltinFunc('str.isalnum', BoolType.get())
    elif name == 'isalpha':
      return BuiltinFunc('str.isalpha', BoolType.get())
    elif name == 'isdigit':
      return BuiltinFunc('str.isdigit', BoolType.get())
    elif name == 'islower':
      return BuiltinFunc('str.islower', BoolType.get())
    elif name == 'isspace':
      return BuiltinFunc('str.isspace', BoolType.get())
    elif name == 'istitle':
      return BuiltinFunc('str.istitle', BoolType.get())
    elif name == 'isupper':
      return BuiltinFunc('str.isupper', BoolType.get())
    elif name == 'join':
      return self.JoinFunc('str.join', self.get(),
                           [STR_ARG])
    elif name == 'ljust':
      return BuiltinFunc('str.ljust', self.get(),
                         [INT_ARG], 
                         [STR_ARG])
    elif name == 'lower':
      return BuiltinFunc('str.lower', self.get())
    elif name == 'lstrip':
      return BuiltinFunc('str.lstrip', self.get(),
                         [STR_ARG])
    elif name == 'partition':
      return BuiltinFunc('str.partiion', TupleType([self.get(), self.get(), self.get()]),
                         [STR_ARG])
    elif name == 'replace':
      return BuiltinFunc('str.replace', self.get(),
                         [BaseStringType, BaseStringType], [IntType])
    elif name == 'rfind':
      return BuiltinFunc('str.rfind', IntType.get(),
                         [STR_ARG],
                         [INT_ARG, INT_ARG])
    elif name == 'rindex':
      return BuiltinFunc('str.rindex', IntType.get(),
                         [STR_ARG],
                         [INT_ARG, INT_ARG],
                         [ExceptionType('ValueError', 'might not able to find the substring')])             
    elif name == 'rjust':
      return BuiltinFunc('str.rjust', self.get(),
                         [INT_ARG], 
                         [STR_ARG])
    elif name == 'rpartition':
      return BuiltinFunc('str.rpartiion', TupleType([self.get(), self.get(), self.get()]),
                         [STR_ARG])
    elif name == 'rsplit':
      return BuiltinFunc('str.rsplit', ListType([self.get()]),
                         [],
                         [STR_ARG, INT_ARG])
    elif name == 'rstrip':
      return BuiltinFunc('str.rstrip', self.get(),
                         [STR_ARG])
    elif name == 'split':
      return BuiltinFunc('str.split', ListType([self.get()]),
                         [],
                         [STR_ARG, INT_ARG])
    elif name == 'splitlines':
      return BuiltinFunc('str.splitlines', ListType([self.get()]),
                         [],
                         [ANY_ARG])
    elif name == 'startswith':
      return BuiltinFunc('str.startswith', BoolType.get(),
                         [STR_ARG],
                         [INT_ARG, INT_ARG])
    elif name == 'strip':
      return BuiltinFunc('str.strip', self.get(),
                         [STR_ARG])
    elif name == 'swapcase':
      return BuiltinFunc('str.swapcase', self.get())
    elif name == 'title':
      return BuiltinFunc('str.title', self.get())
    elif name == 'upper':
      return BuiltinFunc('str.upper', self.get())
    elif name == 'zfill':
      return BuiltinFunc('str.zfill', self.get(),
                         [INT_ARG])
    raise NodeTypeError

  def get_iter(self):
    return self.get()


class StrType(BaseStringType):
  NAME = 'str'
  def get_attr(self, name):
    if name == 'translate':
      return BuiltinFunc('str.translate', self.get(),
                         [STR_ARG],
                         [STR_ARG],
                         [ExceptionType('ValueError', 'table must be 256 chars long')])
    return BaseStringType.get_attr(self, name)
    
class UnicodeType(BaseStringType):
  NAME = 'unicode'
  def get_attr(self, name):
    if name == 'isdecimal':
      return BuiltinFunc('unicode.isdecimal', BoolType.get())
    elif name == 'isnumeric':
      return BuiltinFunc('unicode.isnumeric', BoolType.get())
    elif name == 'translate':
      return XXX
      return BuiltinFunc('unicode.translate', self.get(),
                         [STR_ARG])
    return BaseStringType.get_attr(self, name)


##  ListType
##
class ListType(BuiltinAggregateType):

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

  ##  Method
  ##
  class AppendMethod(SimpleTypeNode):

    def __init__(self, target):
      SimpleTypeNode.__init__(self)
      self.target = target
      return

    def __repr__(self):
      return '%r.append' % self.target

    def call(self, caller, args):
      args[0].connect(self.target.elem)
      return BuiltinFunc(NoneType.get(), [])

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

  def get_element(self, subs, write=False):
    return self.elem

  def get_iter(self):
    return self.elem

  def get_attr(self, name):
    if name == 'append':
      return self.AppendMethod(self)
    elif name == 'count':
      return BuiltinFunc('list.count', IntType.get(),
                         [ANY_ARG])
    elif name == 'extend':
      return self.ExtendMethod(self)
    elif name == 'index':
      return BuiltinFunc('list.index', IntType.get(),
                         [ANY_ARG],
                         [INT_ARG, INT_ARG],
                         [ExceptionType('ValueError', 'might not able to find the element')])
    elif name == 'insert':
      return self.InsertMethod(self)
    elif name == 'pop':
      return BuiltinFunc('list.pop', NoneType.get(),
                         [],
                         [INT_ARG],
                         [ExceptionType('IndexError', 'might be out of range')])
    elif name == 'remove':
      return BuiltinFunc('list.remove', NoneType.get(),
                         [ANY_ARG])
    elif name == 'reverse':
      return BuiltinFunc('list.remove', NoneType.get())
    elif name == 'sort':
      return self.SortMethod(NoneType.get())
    raise NodeTypeError


##  DictType
##
class DictType(BuiltinAggregateType):

  ##  Item
  class Item(CompoundTypeNode):

    def __init__(self, objs):
      CompoundTypeNode.__init__(self)
      for obj in objs:
        obj.connect(self)
      return

  def __init__(self, items):
    self.key = self.Item( k for (k,v) in items )
    self.value = self.Item( v for (k,v) in items )
    BuiltinAggregateType.__init__(self)
    return
  
  def __repr__(self):
    return '{%s: %s}' % (self.key, self.value)

  def __eq__(self, obj):
    return (isinstance(obj, DictType) and
            self.key == obj.key and
            self.value == obj.value)
  def __hash__(self):
    return hash((self.key, self.value))

  def desc1(self, done):
    return '{%s: %s}' % (self.key.desc1(done), self.value.desc1(done))

  def bind(self, key, value):
    self.key.bind(key)
    self.value.bind(value)
    return

  def get_element(self, subs, write=False):
    assert len(subs) == 1
    if write:
      for k in subs:
        k.connect(self.key)
    return self.value

  def get_attr(self, name):
    if name == 'clear':
      return XXX
    elif name == 'copy':
      return XXX
    elif name == 'fromkeys':
      return XXX
    elif name == 'get':
      return XXX
    elif name == 'has_key':
      return XXX
    elif name == 'items':
      return XXX
    elif name == 'iteritems':
      return XXX
    elif name == 'iterkeys':
      return XXX
    elif name == 'itervalues':
      return XXX
    elif name == 'keys':
      return XXX
    elif name == 'pop':
      return XXX
    elif name == 'popitem':
      return XXX
    elif name == 'setdefault':
      return XXX
    elif name == 'update':
      return XXX
    elif name == 'values':
      return XXX
    raise NodeTypeError


##  TupleType
##
class TupleType(BuiltinAggregateType):

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
    SimpleTypeNode.__init__(self)
    self.elements = elements
    self.loc = loc
    self.elemall = self.ElementAll(elements)
    return
  
  def __repr__(self):
    return '(%s)' % ','.join(map(repr, self.elements))

  def desc1(self, done):
    return '(%s)' % ','.join( elem.desc1(done) for elem in self.elements )

  def get_nth(self, i):
    return self.elements[i]

  def get_element(self, subs, write=False):
    if write:
      raise NodeTypeError('cannot change tuple')
    return self.elemall

  def get_iter(self):
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

  def __init__(self, parent_frame, tupobj, nelems):
    CompoundTypeNode.__init__(self)
    loc = None
    if isinstance(tupobj, TupleType):
      loc = tupobj.loc
    self.tupobj = tupobj
    self.elems = [ self.Element(self, i) for i in xrange(nelems) ]
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.tupobj.connect(self, self.recv_tupobj)
    return

  def __repr__(self):
    return '<TupleUnpack: %r>' % (self.tupobj,)

  def get_element(self, i, write=False):
    return self.elems[i]

  def recv_tupobj(self, src):
    assert src is self.tupobj
    for obj in src.types:
      if isinstance(obj, TupleType):
        if len(obj.elements) != len(self.elems):
          self.raise_expt(ExceptionType(
            'ValueError',
            'tuple elements mismatch: len(%r) != %r' % (obj, len(self.elems))))
        else:
          for (i,elem) in enumerate(obj.elements):
            elem.connect(self.elems[i])
      if isinstance(obj, ListType):
        for elem in self.elems:
          obj.elem.connect(elem)
      else:
        self.raise_expt(ExceptionType(
          'TypeError',
          'not unpackable: %r' % src))
    return


##  GeneratorType
##
class GeneratorType(BuiltinAggregateType):

  def __init__(self, yields):
    BuiltinAggregateType.__init__(self)
    self.elem = ListType.Element(yields)
    return

  def __repr__(self):
    return '(%s ...)' % self.elem

  def desc1(self, done):
    return '(%s ...)' % self.elem.desc1(done)

  def get_iter(self):
    return self.elem


##  GeneratorSlot
##
class GeneratorSlot(CompoundTypeNode):

  def __init__(self, value):
    CompoundTypeNode.__init__(self)
    self.types.add(self)
    self.value = value
    return


##  FileType
##
class FileType(BuiltinType):

  def __init__(self, args):
    BuiltinType.__init__(self)
    return


##  ObjectType
##
class ObjectType(BuiltinType):
  pass


#
BUILTIN_TYPE = dict(
  (cls.NAME, cls.get()) for cls in
  ( NoneType, BoolType, IntType, LongType, FloatType, StrType, UnicodeType )
  )
INT_ARG = ( IntType.get(), LongType.get() )
STR_ARG = ( StrType.get(), UnicodeType.get() )
ANY_ARG = True
