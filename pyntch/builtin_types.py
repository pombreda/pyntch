#!/usr/bin/env python

from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError
from frame import ExceptionType, ExceptionRaiser


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


##  ConstFuncType
##
class ConstFuncType(SimpleTypeNode):

  def __init__(self, obj):
    SimpleTypeNode.__init__(self)
    self.obj = obj
    return

  def __repr__(self):
    return '<Const %r>' % self.obj

  def connect_expt(self, frame):
    return
  
  def call(self, caller, args):
    return self.obj


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
  def get_attr(self, name):
    if name == 'capitalize':
      return XXX
    elif name == 'center':
      return XXX
    elif name == 'count':
      return XXX
    elif name == 'decode':
      return XXX
    elif name == 'encode':
      return XXX
    elif name == 'endswith':
      return XXX
    elif name == 'expandtabs':
      return XXX
    elif name == 'find':
      return XXX
    elif name == 'index':
      return XXX
    elif name == 'isalnum':
      return XXX
    elif name == 'isalpha':
      return XXX
    elif name == 'isdigit':
      return XXX
    elif name == 'islower':
      return XXX
    elif name == 'isspace':
      return XXX
    elif name == 'istitle':
      return XXX
    elif name == 'isupper':
      return XXX
    elif name == 'join':
      return XXX
    elif name == 'ljust':
      return XXX
    elif name == 'lower':
      return XXX
    elif name == 'lstrip':
      return XXX
    elif name == 'partition':
      return XXX
    elif name == 'replace':
      return XXX
    elif name == 'rfind':
      return XXX
    elif name == 'rindex':
      return XXX
    elif name == 'rjust':
      return XXX
    elif name == 'rpartition':
      return XXX
    elif name == 'rsplit':
      return XXX
    elif name == 'rstrip':
      return XXX
    elif name == 'split':
      return XXX
    elif name == 'splitlines':
      return XXX
    elif name == 'startswith':
      return XXX
    elif name == 'strip':
      return XXX
    elif name == 'swapcase':
      return XXX
    elif name == 'title':
      return XXX
    elif name == 'translate':
      return XXX
    elif name == 'upper':
      return XXX
    elif name == 'zfill':
      return XXX
    raise NodeTypeError

class StrType(BaseStringType):
  NAME = 'str'
    
class UnicodeType(BaseStringType):
  NAME = 'unicode'
  def get_attr(self, name):
    if name == 'isdecimal':
      return XXX
    elif name == 'isnumeric':
      return XXX
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

  class AppendMethod(SimpleTypeNode):

    def __init__(self, target):
      SimpleTypeNode.__init__(self)
      self.target = target
      return

    def __repr__(self):
      return '%r.append' % self.target

    def call(self, caller, args):
      args[0].connect(self.target.elem)
      return ConstFuncType(NoneType.get())

  #
  def __init__(self, elems):
    SimpleTypeNode.__init__(self)
    self.elem = self.Element(elems)
    return
  
  def __repr__(self):
    return '[%s]' % self.elem

  def desc1(self, done):
    return '[%s]' % self.elem.desc1(done)

  def get_element(self, subs, write=False):
    return self.elem

  def bind(self, obj):
    obj.connect(self.elem)
    return

  def get_iter(self):
    return self.elem

  def get_attr(self, name):
    if name == 'append':
      return self.AppendMethod(self)
    elif name == 'remove':
      return self.ListRemove(self)
    elif name == 'count':
      return self.ListCount(self)
    elif name == 'extend':
      return self.ListExtend(self)
    elif name == 'index':
      return self.ListIndex(self)
    elif name == 'pop':
      return self.ListPop(self)
    elif name == 'insert':
      return self.AppendMethod(self)
    elif name == 'remove':
      return self.AppendMethod(self)
    elif name == 'reverse':
      return ConstFuncType(NoneType.get())
    elif name == 'sort':
      return ConstFuncType(NoneType.get())
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
    SimpleTypeNode.__init__(self)
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
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.tupobj = tupobj
    self.elems = [ self.Element(self, i) for i in xrange(nelems) ]
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
    SimpleTypeNode.__init__(self)
    self.elem = ListType.Element([ slot.value for slot in yields ])
    return

  def __repr__(self):
    return '(%s ...)' % self.elem

  def desc1(self, done):
    return '(%s ...)' % self.elem.desc1(done)

  def get_iter(self):
    return self.elem


#
BUILTIN_TYPE = dict(
  (cls.NAME, cls.get()) for cls in
  ( NoneType, BoolType, IntType, LongType, FloatType, StrType, UnicodeType )
  )
