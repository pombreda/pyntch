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

  def accept_arg(self, caller, i):
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
          arg1.connect(self.accept_arg(caller, i))
    for expt in self.expts:
      caller.raise_expt(expt)
    return self.retval


##  NoneType
##
class NoneType(BuiltinType):
  NAME = 'NoneType'
  def __repr__(self):
    return '<None>'

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
    def accept_arg(self, caller, i):
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

  def get_iter(self, caller):
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

  ##  Methods
  ##
  class AppendMethod(BuiltinFunc):
    def __init__(self, listobj):
      BuiltinFunc.__init__(self, 'list.append', NoneType.get(), [ANY_ARG])
      self.listobj = listobj
      return
    def __repr__(self):
      return '%r.append' % self.listobj
    def accept_arg(self, caller, _):
      return self.listobj.elem

  class ExtendMethod(BuiltinFunc):
    def __init__(self, listobj):
      BuiltinFunc.__init__(self, 'list.extend', NoneType.get(), [ANY_ARG])
      self.listobj = listobj
      return
    def __repr__(self):
      return '%r.extend' % self.listobj
    def accept_arg(self, caller, i):
      XXX
      return ElementExtender(caller, self.listobj.elem)
    
  class InsertMethod(BuiltinFunc):
    def __init__(self, listobj):
      BuiltinFunc.__init__(self, 'list.insert', NoneType.get(), [INT_ARG, ANY_ARG], [],
                           [ExceptionType('IndexError', 'might be out of range')])
      self.listobj = listobj
      return
    def __repr__(self):
      return '%r.extend' % self.listobj
    def accept_arg(self, caller, i):
      if i == 0:
        return self.listobj.elem
      else:
        return BuiltinFunc.accept_arg(self, caller, i)
      
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
                         [ANY_ARG],
                         [ExceptionType('ValueError', 'might not able to remove the element')])
    elif name == 'reverse':
      return BuiltinFunc('list.remove', NoneType.get())
    elif name == 'sort':
      return self.SortMethod(NoneType.get())
    raise NodeTypeError

  def get_element(self, caller, subs, write=False):
    caller.raise_expt(ExceptionType(
      'IndexError',
      '%r index might be out of range.' % self))
    return self.elem

  def get_iter(self, caller):
    return self.elem


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
    self.items = items
    self.default = CompoundTypeNode()
    self.key = self.Item( k for (k,v) in items )
    self.value = self.Item( v for (k,v) in items )
    NoneType.get().connect(self.default)
    BuiltinAggregateType.__init__(self)
    return
  
  def __repr__(self):
    return '{%s: %s}' % (self.key, self.value)

  def copy(self):
    return DictType(self.items)

  def desc1(self, done):
    return '{%s: %s}' % (self.key.desc1(done), self.value.desc1(done))

  def bind(self, key, value):
    key.connect(self.key)
    value.connect(self.value)
    return

  def get_attr(self, name):
    if name == 'clear':
      return BuiltinFunc('dict.claer', NoneType.get())
    elif name == 'copy':
      return BuiltinFunc('dict.copy', self.copy())
    elif name == 'fromkeys':
      return XXX
    elif name == 'get':
      return XXX
    elif name == 'has_key':
      return BuiltinFunc('dict.has_key', BoolType.get(), [ANY_ARG])
    elif name == 'items':
      return BuiltinFunc('dict.items', ListType([ TupleType([self.key, self.value]) ]))
    elif name == 'iteritems':
      return BuiltinFunc('dict.iteritems', IterType([ TupleType([self.key, self.value]) ]))
    elif name == 'iterkeys':
      return BuiltinFunc('dict.iterkeys', IterType([ TupleType([self.key]) ]))
    elif name == 'itervalues':
      return BuiltinFunc('dict.itervalues', IterType([ TupleType([self.value]) ]))
    elif name == 'keys':
      return BuiltinFunc('dict.keys', ListType([ TupleType([self.key]) ]))
    elif name == 'pop':
      return XXX
    elif name == 'popitem':
      return BuiltinFunc('dict.popitem', TupleType([self.key, self.value]))
    elif name == 'setdefault':
      return XXX
    elif name == 'update':
      return XXX
    elif name == 'values':
      return BuiltinFunc('dict.keys', ListType([ TupleType([self.key]) ]))
    raise NodeTypeError

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

  def get_element(self, caller, subs, write=False):
    if write:
      caller.raise_expt(ExceptionType(
        'TypeError',
        'tuple does not support assignment.'))
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

  def get_nth(self, i):
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


##  IterType
##
class IterType(BuiltinAggregateType):

  def __init__(self, yields):
    BuiltinAggregateType.__init__(self)
    self.elem = ListType.Element(yields)
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
