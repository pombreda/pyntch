#!/usr/bin/env python

from typenode import SimpleTypeNode, CompoundTypeNode, BuiltinType, NodeTypeError, NodeAttrError
from exception import ExceptionType, ExceptionRaiser, TypeChecker
from builtin_types import BuiltinFunc, BuiltinConstFunc, \
     BoolType, IntType, NoneType, ANY_TYPE


##  BuiltinAggregateObject
##
class BuiltinAggregateObject(SimpleTypeNode):

  TYPEOBJ = 'undefined'

  def __init__(self):
    SimpleTypeNode.__init__(self, self.TYPEOBJ)
    return

  # get_typename()
  # returns the name of the Python type of this object.
  @classmethod
  def get_typename(klass):
    return klass.TYPEOBJ.get_typename()

  # get_null()
  NULL = None
  @classmethod
  def get_null(klass):
    if not klass.NULL:
      klass.NULL = klass([])
    return klass.NULL

# ElementAll
class ElementAll(CompoundTypeNode):
  def __init__(self, elements):
    CompoundTypeNode.__init__(self)
    for elem in elements:
      elem.connect(self)
    return


##  Aggregate Types
##
  
##  List
##
class ListType(BuiltinType, BuiltinFunc):
  
  PYTHON_TYPE = list
  
  class ListConversion(CompoundTypeNode, ExceptionRaiser):
    
    def __init__(self, parent_frame, loc):
      CompoundTypeNode.__init__(self)
      ExceptionRaiser.__init__(self, parent_frame, loc)
      return
    
    def recv(self, src):
      for obj in src.types:
        try:
          elemall = obj.get_iter(self)
          self.update_types(set([ListObject(elemall=elemall)]))
        except NodeTypeError:
          self.raise_expt(ExceptionType(
            'TypeError',
            'cannot convert to list: %s' % obj))
      return
  
  def process_args(self, caller, args):
    if args:
      listobj = self.ListConversion(caller, caller.loc)
      args[0].connect(listobj)
      return listobj
    else:
      return ListObject.get_null()

  def __init__(self):
    BuiltinFunc.__init__(self, 'list', [], [ANY_TYPE])
    return
  
class ListObject(BuiltinAggregateObject):

  TYPEOBJ = ListType.get_type()
  
  def __init__(self, elements=None, elemall=None):
    if elements == None:
      assert elemall != None
      self.elemall = elemall
    else:
      assert elements != None
      self.elemall = ElementAll(elements)
    BuiltinAggregateObject.__init__(self)
    return
  
  def __repr__(self):
    return '[%s]' % self.elemall.describe()

  def __eq__(self, obj):
    return isinstance(obj, ListObject) and self.elemall == obj.elemall
  def __hash__(self):
    return hash(self.elemall)

  @classmethod
  def concat(klass, obj1, obj2):
    assert isinstance(obj1, klass) and isinstance(obj2, klass)
    return klass([obj1.elemall, obj2.elemall])

  @classmethod
  def multiply(klass, obj):
    assert isinstance(obj, klass)
    return obj

  def desc1(self, done):
    return '[%s]' % self.elemall.desc1(done)

  def bind(self, obj):
    obj.connect(self.elemall)
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
    return self.elemall

  def get_iter(self, caller):
    return self.elemall

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
      return self.listobj.elemall

  class ExtendMethod(BuiltinConstFunc):
    
    class ElementExtender(CompoundTypeNode, ExceptionRaiser):
      def __init__(self, parent_frame, elemall, loc):
        self.elemall = elemall
        CompoundTypeNode.__init__(self)
        ExceptionRaiser.__init__(self, parent_frame, loc)
        return
      def recv(self, src):
        for obj in src.types:
          try:
            obj.get_iter(self).connect(self.elemall)
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
      return self.ElementExtender(caller, self.listobj.elemall, caller.loc)
    
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
        return self.listobj.elemall
      else:
        return BuiltinConstFunc.accept_arg(self, caller, i)
      
  class SortMethod(BuiltinConstFunc):
    
    def __init__(self, listobj):
      BuiltinConstFunc.__init__(self, 'list.sort', NoneType.get_object())
      self.listobj = listobj
      return
    
    def __repr__(self):
      return '%r.sort' % self.listobj


##  TupleObject
##
class TupleType(BuiltinType, BuiltinFunc):
  
  PYTHON_TYPE = tuple

  class TupleConversion(CompoundTypeNode, ExceptionRaiser):
    
    def __init__(self, parent_frame, loc):
      CompoundTypeNode.__init__(self)
      ExceptionRaiser.__init__(self, parent_frame, loc)
      return
    
    def recv(self, src):
      for obj in src.types:
        try:
          elemall = obj.get_iter(self)
          self.update_types(set([TupleObject(elemall=elemall)]))
        except NodeTypeError:
          self.raise_expt(ExceptionType(
            'TypeError',
            'cannot convert to tuple: %s' % obj))
      return
  
  def process_args(self, caller, args):
    if args:
      tupobj = self.TupleConversion(caller, caller.loc)
      args[0].connect(tupobj)
      return tupobj
    else:
      return TupleObject.get_null()

  def __init__(self):
    BuiltinFunc.__init__(self, 'tuple', [], [ANY_TYPE])
    return

class TupleObject(BuiltinAggregateObject):

  TYPEOBJ = TupleType.get_type()
  
  def __init__(self, elements=None, loc=None, elemall=None):
    self.elements = elements
    self.loc = loc
    if elements == None:
      assert elemall != None
      self.elemall = elemall
    else:
      assert elemall == None
      self.elemall = ElementAll(elements)
    BuiltinAggregateObject.__init__(self)
    return
  
  def __repr__(self):
    if self.elements == None:
      return '(*%s)' % self.elemall.describe()
    else:
      return '(%s)' % ','.join( elem.describe() for elem in self.elements )

  def __eq__(self, obj):
    return isinstance(obj, TupleObject) and self.elements == obj.elements and self.elemall == obj.elemall
  def __hash__(self):
    return hash(self.elemall)

  @classmethod
  def concat(klass, obj1, obj2):
    assert isinstance(obj1, klass) and isinstance(obj2, klass)
    if obj1.elements == None or obj2.elements == None:
      return klass(elemall=ElementAll([obj1.elemall, obj2.elemall]))
    else:
      return klass(elements=obj1.elements+obj2.elements)

  @classmethod
  def multiply(klass, obj):
    assert isinstance(obj, klass)
    return klass(loc=obj.loc, elemall=obj.elemall)
  
  def desc1(self, done):
    if self.elements == None:
      return '(*%s)' % self.elemall.desc1(done)
    else:
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
  
  #
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
      if obj.is_type(TupleType.get_type()):
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


##  Iterator
##
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

  @classmethod
  def get_typename(klass):
    return 'iterator'

  def desc1(self, done):
    return '(%s, ...)' % self.elemall.desc1(done)

  def get_iter(self, caller):
    return self.elemall


##  GeneratorSlot
##
class GeneratorSlot(CompoundTypeNode):

  def __init__(self, value):
    CompoundTypeNode.__init__(self, [self])
    self.value = value
    return


##  SetObject
##
class SetType(BuiltinType, BuiltinFunc):

  PYTHON_TYPE = set

  class SetConversion(CompoundTypeNode, ExceptionRaiser):
    
    def __init__(self, parent_frame, loc):
      CompoundTypeNode.__init__(self)
      ExceptionRaiser.__init__(self, parent_frame, loc)
      return
    
    def recv(self, src):
      for obj in src.types:
        try:
          elemall = obj.get_iter(self)
          self.update_types(set([SetObject(elemall=elemall)]))
        except NodeTypeError:
          self.raise_expt(ExceptionType(
            'TypeError',
            'cannot convert to set: %s' % obj))
      return
  
  def process_args(self, caller, args):
    if args:
      setobj = self.SetConversion(caller, caller.loc)
      args[0].connect(setobj)
      return setobj
    else:
      return SetObject.get_null()

  def __init__(self):
    BuiltinFunc.__init__(self, 'set', [], [ANY_TYPE])
    return

class SetObject(BuiltinAggregateObject):

  TYPEOBJ = SetType.get_type()
  
  def __init__(self, elements=None, elemall=None):
    if elements == None:
      assert elemall != None
      self.elemall = elemall
    else:
      assert elements != None
      self.elemall = ElementAll(elements)
    BuiltinAggregateObject.__init__(self)
    return
  
  def __repr__(self):
    return '([%s])' % (self.elemall)

  def copy(self):
    return SetObject(elemall=self.elemall)

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
  

##  DictObject
##
class DictType(BuiltinType, BuiltinFunc):
  
  PYTHON_TYPE = dict
  
  def process_args(self, caller, args):
    return DictObject(args)

  def __init__(self):
    BuiltinFunc.__init__(self, 'dict', [], [ANY_TYPE]) # XXX take keyword argument!
    return

class DictObject(BuiltinAggregateObject):

  TYPEOBJ = DictType.get_type()
  
  ##  Item
  class Item(CompoundTypeNode):
    def __init__(self, objs):
      CompoundTypeNode.__init__(self)
      for obj in objs:
        obj.connect(self)
      return

  # dict.get
  class Get(BuiltinConstFunc):
    def __init__(self, dictobj):
      self.dictobj = dictobj
      self.found = CompoundTypeNode()
      dictobj.value.connect(self.found)
      BuiltinConstFunc.__init__(self, 'dict.get', self.found, [ANY_TYPE], [ANY_TYPE])
      return
    def __repr__(self):
      return '%r.get' % self.dictobj
    def accept_arg(self, caller, i):
      if i == 0:
        return None
      return self.found

  # dict.setdefault
  class SetDefault(BuiltinConstFunc):
    def __init__(self, dictobj):
      self.dictobj = dictobj
      BuiltinConstFunc.__init__(self, 'dict.setdefault', dictobj.default, [ANY_TYPE], [ANY_TYPE])
      return
    def __repr__(self):
      return '%r.setdefault' % self.dictobj
    def accept_arg(self, caller, i):
      if i == 1:
        self.args[i].connect(self.dictobj.value)
      return None

  def __init__(self, items=None, key=None, value=None):
    if items != None:
      assert key == None and value == None
      self.key = self.Item( k for (k,v) in items )
      self.value = self.Item( v for (k,v) in items )
    else:
      assert key != None and value != None
      self.key = CompoundTypeNode([key])
      self.value = CompoundTypeNode([value])
    self.default = CompoundTypeNode()
    NoneType.get_object().connect(self.default)
    self.value.connect(self.default)
    BuiltinAggregateObject.__init__(self)
    return
  
  def __repr__(self):
    return '{%s: %s}' % (self.key, self.value)

  def copy(self):
    return DictObject(key=self.key, value=self.value)

  def desc1(self, done):
    return '{%s: %s}' % (self.key.desc1(done), self.value.desc1(done))

  def bind(self, key, value):
    key.connect(self.key)
    value.connect(self.value)
    return

  def get_attr(self, name):
    if name == 'clear':
      return BuiltinConstFunc('dict.clear', NoneType.get_object())
    elif name == 'copy':
      return BuiltinConstFunc('dict.copy', self.copy())
    elif name == 'fromkeys':
      return self.FromKeys()
    elif name == 'get':
      return self.Get(self)
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
      return self.Get(self)
    elif name == 'popitem':
      return BuiltinConstFunc('dict.popitem', TupleObject([self.key, self.value]))
    elif name == 'setdefault':
      return self.SetDefault(self)
    elif name == 'update':
      return self.Update(self)
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
  

