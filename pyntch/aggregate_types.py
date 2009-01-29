#!/usr/bin/env python

from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, \
     BuiltinType, BuiltinObject
from exception import TypeChecker, \
     TypeErrorType, IndexErrorType, ValueErrorType, KeyErrorType
from builtin_types import InternalFunc, InternalConstFunc, BoolType, IntType, NoneType, ANY_TYPE



##  Aggregate Types
##
class BuiltinAggregateType(BuiltinType):
  
  # get_object() now creates an actual instance.
  @classmethod
  def get_object(klass, *args, **kwargs):
    return klass.PYTHON_IMPL(klass.get_typeobj(), *args, **kwargs)


##  BuiltinSequenceObject
##
class BuiltinSequenceObject(BuiltinObject):
  
  def __init__(self, typeobj, elements=None, elemall=None):
    self.elements = elements
    if elemall != None:
      self.elemall = elemall
    else:
      self.elemall = CompoundTypeNode(elements or [])
    BuiltinObject.__init__(self, typeobj)
    return

  def equal(self, obj, done=None):
    if obj.__class__ is not self.__class__: return False
    return self.elemall.equal(obj.elemall, done)


##  List
##
class ListObject(BuiltinSequenceObject):
  
  def __repr__(self):
    return '[%s]' % self.elemall.describe()

  def desc1(self, done):
    return '[%s]' % self.elemall.desc1(done)

  def bind(self, obj):
    obj.connect(self.elemall)
    return

  def get_attr(self, name, write=False):
    if name == 'append':
      return self.AppendMethod(self)
    elif name == 'count':
      return InternalConstFunc('list.count', IntType.get_object(), [ANY_TYPE])
    elif name == 'extend':
      return self.ExtendMethod(self)
    elif name == 'index':
      return InternalConstFunc('list.index', IntType.get_object(), [ANY_TYPE], [IntType, IntType],
                               [ValueErrorType.maybe('might not able to find the element.')])
    elif name == 'insert':
      return self.InsertMethod(self)
    elif name == 'pop':
      return InternalConstFunc('list.pop', NoneType.get_object(), [], [IntType],
                              [ValueErrorType.maybe('might be empty list or out of range.')])
    elif name == 'remove':
      return InternalConstFunc('list.remove', NoneType.get_object(), [ANY_TYPE],
                              [ValueErrorType.maybe('might not able to remove the element.')])
    elif name == 'reverse':
      return InternalConstFunc('list.remove', NoneType.get_object())
    elif name == 'sort':
      return self.SortMethod(NoneType.get_object())
    raise NodeAttrError(name)

  def get_element(self, frame, subs, write=False):
    frame.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self.elemall

  def get_iter(self, frame):
    return IterType.get_object(elemall=self.elemall)

  ##  Methods
  ##
  class AppendMethod(InternalConstFunc):
    def __init__(self, listobj):
      self.listobj = listobj
      InternalConstFunc.__init__(self, 'list.append', NoneType.get_object(), [ANY_TYPE])
      return
    def __repr__(self):
      return '%r.append' % self.listobj
    def accept_arg(self, frame, _):
      return self.listobj.elemall

  class ExtendMethod(InternalConstFunc):
    
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
      InternalConstFunc.__init__(self, 'list.extend', NoneType.get_object(), [ANY_TYPE])
      self.listobj = listobj
      return
    def __repr__(self):
      return '%r.extend' % self.listobj
    def accept_arg(self, frame, i):
      return self.ElementExtender(frame, self.listobj.elemall)
    
  class InsertMethod(InternalConstFunc):
    
    def __init__(self, listobj):
      InternalConstFunc.__init__(self, 'list.insert', NoneType.get_object(), [IntType, ANY_TYPE], [],
                                 [IndexErrorType.maybe('might be out of range.')])
      self.listobj = listobj
      return
    
    def __repr__(self):
      return '%r.extend' % self.listobj
    
    def accept_arg(self, frame, i):
      if i == 0:
        return self.listobj.elemall
      else:
        return InternalConstFunc.accept_arg(self, frame, i)
      
  class SortMethod(InternalConstFunc):
    
    def __init__(self, listobj):
      InternalConstFunc.__init__(self, 'list.sort', NoneType.get_object())
      self.listobj = listobj
      return
    
    def __repr__(self):
      return '%r.sort' % self.listobj


##  ListType
##
class ListType(BuiltinAggregateType, InternalFunc):
  
  PYTHON_TYPE = list
  PYTHON_IMPL = ListObject
  
  @classmethod
  def concat(klass, obj1, obj2):
    return klass.get_object([obj1.elemall, obj2.elemall])

  @classmethod
  def multiply(klass, obj):
    return obj

  class ListConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.listobj = ListType.get_object()
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
      return ListType.get_object()

  def __init__(self):
    InternalFunc.__init__(self, 'list', [], [ANY_TYPE])
    return

  
##  TupleObject
##
class TupleObject(BuiltinSequenceObject):
  
  def __repr__(self):
    if self.elements == None:
      return '(*%s)' % self.elemall.describe()
    else:
      return '(%s)' % ','.join( obj.describe() for obj in self.elements )

  @classmethod
  def concat(klass, obj1, obj2):
    assert isinstance(obj1, klass) and isinstance(obj2, klass)
    if obj1.elements == None or obj2.elements == None:
      return klass(elemall=CompoundTypeNode([obj1.elemall, obj2.elemall]))
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
    return IterType.get_object(elemall=self.elemall)
  

##  TupleType
##
class TupleType(BuiltinAggregateType, InternalFunc):
  
  PYTHON_TYPE = tuple
  PYTHON_IMPL = TupleObject

  class TupleConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.tupleobj = TupleType.get_object()
      CompoundTypeNode.__init__(self)
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
      return TupleType.get_object()

  def __init__(self):
    InternalFunc.__init__(self, 'tuple', [], [ANY_TYPE])
    return


##  SetObject
##
class SetObject(BuiltinSequenceObject):
  
  def __repr__(self):
    return '([%s])' % (self.elemall)

  def copy(self):
    return SetType.get_object(elemall=self.elemall)

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
  

##  SetType
##
class SetType(BuiltinAggregateType, InternalFunc):

  PYTHON_TYPE = set
  PYTHON_IMPL = SetObject

  class SetConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.setobj = SetType.get_object()
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
      return SetType.get_object()

  def __init__(self):
    InternalFunc.__init__(self, 'set', [], [ANY_TYPE])
    return


##  IterObject
##
class IterObject(BuiltinSequenceObject):
  
  def __repr__(self):
    return '(%s, ...)' % self.elemall

  def desc1(self, done):
    return '(%s, ...)' % self.elemall.desc1(done)

  def get_iter(self, frame):
    return self

  def get_attr(self, name, write=False):
    if name == 'next':
      return InternalConstFunc('iter.next', self.elemall)
    raise NodeAttrError(name)
  

##  IterType
##
class IterType(BuiltinAggregateType):

  PYTHON_IMPL = IterObject

  @classmethod
  def get_name(klass):
    return 'iterator'


##  DictObject
##
class DictObject(BuiltinObject):
  
  # dict.get
  class Get(InternalConstFunc):
    def __init__(self, dictobj):
      self.dictobj = dictobj
      self.found = CompoundTypeNode()
      dictobj.value.connect(self.found)
      InternalConstFunc.__init__(self, 'dict.get', self.found, [ANY_TYPE], [ANY_TYPE])
      return
    def __repr__(self):
      return '%r.get' % self.dictobj
    def accept_arg(self, frame, i):
      if i == 0:
        return None
      return self.found

  # dict.setdefault
  class SetDefault(InternalConstFunc):
    def __init__(self, dictobj):
      self.dictobj = dictobj
      InternalConstFunc.__init__(self, 'dict.setdefault', dictobj.default, [ANY_TYPE], [ANY_TYPE])
      return
    def __repr__(self):
      return '%r.setdefault' % self.dictobj
    def accept_arg(self, frame, i):
      if i == 1:
        self.args[i].connect(self.dictobj.value)
      return None

  def __init__(self, typeobj, items=None, key=None, value=None):
    if items != None:
      assert key == None and value == None
      self.key = CompoundTypeNode( k for (k,v) in items )
      self.value = CompoundTypeNode( v for (k,v) in items )
    elif key != None and value != None:
      self.key = CompoundTypeNode([key])
      self.value = CompoundTypeNode([value])
    else:
      self.key = CompoundTypeNode()
      self.value = CompoundTypeNode()
    self.default = CompoundTypeNode([NoneType.get_object()])
    self.value.connect(self.default)
    BuiltinObject.__init__(self, typeobj)
    return
  
  def __repr__(self):
    return '{%s: %s}' % (self.key, self.value)

  def equal(self, obj, done=None):
    if not isinstance(obj, DictObject): return False
    return self.key.equal(obj.key, done) and self.value.equal(obj.value, done)
  
  def copy(self):
    return DictType.get_object(key=self.key, value=self.value)

  def desc1(self, done):
    return '{%s: %s}' % (self.key.desc1(done), self.value.desc1(done))

  def bind(self, key, value):
    key.connect(self.key)
    value.connect(self.value)
    return

  def get_attr(self, name, write=False):
    if name == 'clear':
      return InternalConstFunc('dict.clear', NoneType.get_object())
    elif name == 'copy':
      return InternalConstFunc('dict.copy', self.copy())
    elif name == 'fromkeys':
      return self.FromKeys()
    elif name == 'get':
      return self.Get(self)
    elif name == 'has_key':
      return InternalConstFunc('dict.has_key', BoolType.get_object(), [ANY_TYPE])
    elif name == 'items':
      return InternalConstFunc('dict.items', ListType.get_object([ TupleType.get_object([self.key, self.value]) ]))
    elif name == 'iteritems':
      return InternalConstFunc('dict.iteritems', IterType.get_object([ TupleType.get_object([self.key, self.value]) ]))
    elif name == 'iterkeys':
      return InternalConstFunc('dict.iterkeys', IterType.get_object([ TupleType.get_object([self.key]) ]))
    elif name == 'itervalues':
      return InternalConstFunc('dict.itervalues', IterType.get_object([ TupleType.get_object([self.value]) ]))
    elif name == 'keys':
      return InternalConstFunc('dict.keys', ListType.get_object([ TupleType.get_object([self.key]) ]))
    elif name == 'pop':
      return self.Get(self)
    elif name == 'popitem':
      return InternalConstFunc('dict.popitem', TupleType.get_object([self.key, self.value]))
    elif name == 'setdefault':
      return self.SetDefault(self)
    elif name == 'update':
      return self.Update(self)
    elif name == 'values':
      return InternalConstFunc('dict.keys', ListType.get_object([ TupleType.get_object([self.key]) ]))
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
    return IterType.get_object(elemall=self.key)


##  DictType
##
class DictType(BuiltinAggregateType, InternalFunc):
  
  PYTHON_TYPE = dict
  PYTHON_IMPL = DictObject
  
  class DictConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.dictobj = DictType.get_object()
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
      return DictType.get_object([ (StrType.get_object(), v) for (_,v) in kwargs.iteritems() ])
    if args:
      return self.DictConversion(frame, args[0])
    else:
      return DictType.get_object()

  def __init__(self):
    InternalFunc.__init__(self, 'dict', [], [ANY_TYPE]) # XXX take keyword argument!
    return

