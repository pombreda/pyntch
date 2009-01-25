#!/usr/bin/env python

from typenode import SimpleTypeNode, CompoundTypeNode, BuiltinType, NodeTypeError, NodeAttrError
from exception import TypeChecker, \
     TypeErrorType, IndexErrorType, ValueErrorType, KeyErrorType
from builtin_types import BuiltinFunc, BuiltinConstFunc, \
     ElementAll, IterObject, BoolType, IntType, NoneType, ANY_TYPE


##  BuiltinAggregateObject
##
class BuiltinAggregateObject(SimpleTypeNode):

  TYPEOBJ = None # must be defined by subclass

  def __init__(self):
    SimpleTypeNode.__init__(self, self.TYPEOBJ)
    return

  # get_type()
  # returns the name of the Python type of this object.
  @classmethod
  def get_type(klass):
    assert isinstance(klass.TYPEOBJ, BuiltinType)
    return klass.TYPEOBJ

  # get_null()
  NULL = None
  @classmethod
  def get_null(klass):
    if not klass.NULL:
      klass.NULL = klass([])
    return klass.NULL


##  Aggregate Types
##
  
##  List
##
class ListType(BuiltinFunc):
  
  PYTHON_TYPE = list
  
  class ListConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.listobj = ListObject([])
      CompoundTypeNode.__init__(self, [self.listobj])
      obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_seq(self).connect(self.listobj.elemall)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to list: %s' % obj))
      return
  
  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    if args:
      return self.ListConversion(frame, args[0])
    else:
      return ListObject.get_null()

  def __init__(self):
    BuiltinFunc.__init__(self, 'list', [], [ANY_TYPE])
    return
  
class ListObject(BuiltinAggregateObject):

  TYPEOBJ = ListType.get_typeobj()
  
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

  def equal(self, obj, done):
    if not isinstance(obj, ListObject): return False
    return self.elemall.equal(obj.elemall, done)

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

  def get_attr(self, name, write=False):
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
                         [ValueErrorType.maybe('might not able to find the element.')])
    elif name == 'insert':
      return self.InsertMethod(self)
    elif name == 'pop':
      return BuiltinConstFunc('list.pop', NoneType.get_object(),
                              [],
                              [IntType],
                              [ValueErrorType.maybe('might be empty list or out of range.')])
    elif name == 'remove':
      return BuiltinConstFunc('list.remove', NoneType.get_object(),
                              [ANY_TYPE],
                              [ValueErrorType.maybe('might not able to remove the element.')])
    elif name == 'reverse':
      return BuiltinConstFunc('list.remove', NoneType.get_object())
    elif name == 'sort':
      return self.SortMethod(NoneType.get_object())
    raise NodeAttrError(name)

  def get_element(self, frame, subs, write=False):
    frame.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self.elemall

  def get_iter(self, frame):
    return IterObject(elemall=self.elemall)

  ##  Methods
  ##
  class AppendMethod(BuiltinConstFunc):
    def __init__(self, listobj):
      self.listobj = listobj
      BuiltinConstFunc.__init__(self, 'list.append', NoneType.get_object(), [ANY_TYPE])
      return
    def __repr__(self):
      return '%r.append' % self.listobj
    def accept_arg(self, frame, _):
      return self.listobj.elemall

  class ExtendMethod(BuiltinConstFunc):
    
    class ElementExtender(CompoundTypeNode):
      def __init__(self, frame, elemall):
        self.frame = frame
        self.elemall = elemall
        CompoundTypeNode.__init__(self)
        return
      def recv(self, src):
        for obj in src:
          try:
            obj.get_seq(self).connect(self.elemall)
          except NodeTypeError:
            self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
        return

    def __init__(self, listobj):
      BuiltinConstFunc.__init__(self, 'list.extend', NoneType.get_object(), [ANY_TYPE])
      self.listobj = listobj
      return
    def __repr__(self):
      return '%r.extend' % self.listobj
    def accept_arg(self, frame, i):
      return self.ElementExtender(frame, self.listobj.elemall)
    
  class InsertMethod(BuiltinConstFunc):
    
    def __init__(self, listobj):
      BuiltinConstFunc.__init__(self, 'list.insert', NoneType.get_object(), [IntType, ANY_TYPE], [],
                                [IndexErrorType.maybe('might be out of range.')])
      self.listobj = listobj
      return
    
    def __repr__(self):
      return '%r.extend' % self.listobj
    
    def accept_arg(self, frame, i):
      if i == 0:
        return self.listobj.elemall
      else:
        return BuiltinConstFunc.accept_arg(self, frame, i)
      
  class SortMethod(BuiltinConstFunc):
    
    def __init__(self, listobj):
      BuiltinConstFunc.__init__(self, 'list.sort', NoneType.get_object())
      self.listobj = listobj
      return
    
    def __repr__(self):
      return '%r.sort' % self.listobj


##  TupleObject
##
class TupleType(BuiltinFunc):
  
  PYTHON_TYPE = tuple

  class TupleConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.tupleobj = TupleObject([])
      CompoundTypeNode.__init__(self, [])
      obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_seq(self).connect(self.tupleobj.elemall)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to tuple: %s' % obj))
      return
  
  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    if args:
      return self.TupleConversion(frame, args[0])
    else:
      return TupleObject.get_null()

  def __init__(self):
    BuiltinFunc.__init__(self, 'tuple', [], [ANY_TYPE])
    return

class TupleObject(BuiltinAggregateObject):

  TYPEOBJ = TupleType.get_typeobj()
  
  def __init__(self, elements=None, elemall=None):
    self.elements = elements
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
      return '(%s)' % ','.join( obj.describe() for obj in self.elements )

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
    return klass(elemall=obj.elemall)
  
  def desc1(self, done):
    if self.elements == None:
      return '(*%s)' % self.elemall.desc1(done)
    else:
      return '(%s)' % ','.join( obj.desc1(done) for obj in self.elements )

  def get_element(self, frame, subs, write=False):
    if write:
      frame.raise_expt(TypeErrorType.occur('cannot assign to a tuple.'))
    else:
      frame.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self.elemall

  def get_iter(self, frame):
    return IterObject(elemall=self.elemall)
  

##  SetObject
##
class SetType(BuiltinFunc):

  PYTHON_TYPE = set

  class SetConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.setobj = SetObject([])
      CompoundTypeNode.__init__(self)
      obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_seq(self).connect(self.setobj.elemall)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to set: %s' % obj))
      return
  
  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    if args:
      return self.SetConversion(frame, args[0])
    else:
      return SetObject.get_null()

  def __init__(self):
    BuiltinFunc.__init__(self, 'set', [], [ANY_TYPE])
    return

class SetObject(BuiltinAggregateObject):

  TYPEOBJ = SetType.get_typeobj()
  
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

  def get_attr(self, name, write=False):
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
class DictType(BuiltinFunc):
  
  PYTHON_TYPE = dict
  
  class DictConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.dictobj = DictObject([])
      CompoundTypeNode.__init__(self, [self.dictobj])
      obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_seq(self).connect(self, self.recv_pair)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to dict: %s' % obj))
      return
  
    def recv_pair(self, src):
      for obj in src:
        try:
          if obj.is_type(TupleType.get_typeobj()) and obj.elements:
            if len(obj.elements) == 2:
              (k,v) = obj.elements
              k.connect(self.dictobj.key)
              v.connect(self.dictobj.value)
            else:
              self.frame.raise_expt(TypeErrorType.occur('cannot convert to dict: tuple length is not 2: %s' % obj))
            continue
          elem = obj.get_seq(self)
          elem.connect(self, self.dictobj.key)
          elem.connect(self, self.dictobj.value)
          self.frame.raise_expt(TypeErrorType.maybe('might not be able to convert to dict: %s' % obj))
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to dict: %s' % obj))
      return
    
  def process_args(self, frame, args, kwargs):
    if kwargs:
      return DictObject([ (StrType.get_object(), v) for (_,v) in kwargs.iteritems() ])
    if args:
      return self.DictConversion(frame, args[0])
    else:
      return DictObject.get_null()

  def __init__(self):
    BuiltinFunc.__init__(self, 'dict', [], [ANY_TYPE]) # XXX take keyword argument!
    return

class DictObject(BuiltinAggregateObject):

  TYPEOBJ = DictType.get_typeobj()
  
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
    def accept_arg(self, frame, i):
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
    def accept_arg(self, frame, i):
      if i == 1:
        self.args[i].connect(self.dictobj.value)
      return None

  def __init__(self, items=None, key=None, value=None):
    if items != None:
      assert key == None and value == None
      self.key = ElementAll( k for (k,v) in items )
      self.value = ElementAll( v for (k,v) in items )
    elif key != None and value != None:
      self.key = CompoundTypeNode([key])
      self.value = CompoundTypeNode([value])
    else:
      self.key = CompoundTypeNode()
      self.value = CompoundTypeNode()
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

  def get_attr(self, name, write=False):
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

  def get_element(self, frame, subs, write=False):
    assert len(subs) == 1
    key = subs[0]
    if write:
      key.connect(self.key)
    else:
      frame.raise_expt(KeyErrorType.maybe('might not have the key: %r' % key))
    return self.value

  def get_iter(self, frame):
    return IterObject(elemall=self.key)
