#!/usr/bin/env python
from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, \
     BuiltinType, BuiltinObject
from exception import TypeChecker, \
     TypeErrorType, IndexErrorType, ValueErrorType, KeyErrorType
from builtin_types import BuiltinCallable, BuiltinConstCallable, BoolType, IntType, StrType, NoneType, ANY



##  Aggregate Types
##
class BuiltinSequenceType(BuiltinType):
  
  @classmethod
  def create_sequence(klass, elements=None, elemall=None):
    return klass.TYPE_INSTANCE(klass.get_typeobj(), elements=elements, elemall=elemall)



##  BuiltinSequenceObject
##
class BuiltinSequenceObject(BuiltinObject):
  
  class SequenceConverter(CompoundTypeNode):
    def __init__(self, frame, target, src):
      self.frame = frame
      self.target = target
      CompoundTypeNode.__init__(self, [self.target, src])
      return
    def __repr__(self):
      return 'convert(%r)' % self.target
    def recv(self, src):
      for obj in src:
        try:
          obj.get_seq(self).connect(self.target.elemall)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
      return
  
  class SequenceAppender(BuiltinConstCallable):
    def __init__(self, name, target, retype=NoneType.get_object(), args=None, optargs=None):
      self.target = target
      BuiltinConstCallable.__init__(self, name, retype, args=args, optargs=optargs)
      return
    def __repr__(self):
      return '%r.append' % self.target
    def accept_arg(self, frame, _):
      return self.target.elemall

  class SequenceExtender(BuiltinConstCallable):
    class Processor(CompoundTypeNode):
      def __init__(self, frame, target):
        self.frame = frame
        self.target = target
        CompoundTypeNode.__init__(self)
        return
      def recv(self, src):
        for obj in src:
          try:
            obj.get_seq(self).connect(self.target.elemall)
          except NodeTypeError:
            self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
        return
    def __init__(self, name, target, retype=NoneType.get_object(), args=None, optargs=None):
      self.target = target
      BuiltinConstCallable.__init__(self, name, retype, args=args, optargs=optargs)
      return
    def __repr__(self):
      return '%r.extend' % self.target
    def accept_arg(self, frame, _):
      return self.Processor(frame, self.target)

  def __init__(self, typeobj, elements=None, elemall=None):
    self.elements = elements
    if elemall != None:
      self.elemall = CompoundTypeNode([elemall])
    else:
      self.elemall = CompoundTypeNode(elements or [])
    BuiltinObject.__init__(self, typeobj)
    return

  def get_iter(self, frame):
    return IterType.create_sequence(elemall=self.elemall)


##  List
##
class ListObject(BuiltinSequenceObject):

  def desc1(self, done):
    return '[%s]' % self.elemall.desc1(done)

  def equal(self, obj, done=None):
    if not isinstance(obj, ListObject): return False
    return self.elemall.equal(obj.elemall, done)
  
  def get_attr(self, name, write=False):
    if name == 'append':
      return self.SequenceAppender('list.append', self, args=[ANY])
    elif name == 'count':
      return BuiltinConstCallable('list.count', IntType.get_object(), [ANY])
    elif name == 'extend':
      return self.SequenceExtender('list.extend', self, args=[ANY])
    elif name == 'index':
      return BuiltinConstCallable('list.index', IntType.get_object(), [ANY], [IntType, IntType],
                               expts=[ValueErrorType.maybe('might not able to find the element.')])
    elif name == 'insert':
      return self.InsertMethod('list.insert', self, [IntType, ANY])
    elif name == 'pop':
      return BuiltinConstCallable('list.pop', self.elemall, [], [IntType],
                               expts=[ValueErrorType.maybe('might be empty list or out of range.')])
    elif name == 'remove':
      return BuiltinConstCallable('list.remove', NoneType.get_object(), [ANY],
                               expts=[ValueErrorType.maybe('might not able to remove the element.')])
    elif name == 'reverse':
      return BuiltinConstCallable('list.remove', NoneType.get_object())
    elif name == 'sort':
      return XXX #self.SortMethod('list.sort')
    raise NodeAttrError(name)

  def get_element(self, frame, subs, write=False):
    frame.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self.elemall

  ##  Methods
  ##
  class InsertMethod(BuiltinSequenceObject.SequenceAppender):
    def accept_arg(self, frame, i):
      if i == 0:
        return BuiltinConstCallable.accept_arg(self, frame, i)
      return BuiltinSequenceObject.SequenceAppender.accept_arg(self, frame, i)
      
  class SortMethod(BuiltinConstCallable):
    def __init__(self, name):
      BuiltinConstCallable.__init__(self, name, NoneType.get_object())
      return

    
##  ListType
##
class ListType(BuiltinSequenceType, BuiltinCallable):
  
  TYPE_NAME = 'list'
  TYPE_INSTANCE = ListObject
  
  @classmethod
  def concat(klass, obj1, obj2):
    return klass.create_sequence([obj1.elemall, obj2.elemall])

  @classmethod
  def multiply(klass, obj):
    return obj
  
  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    if args:
      return BuiltinSequenceObject.SequenceConverter(frame, ListType.create_sequence(), args[0])
    else:
      return ListType.create_sequence()

  def __init__(self):
    BuiltinCallable.__init__(self, 'list', [], [ANY])
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

  def equal(self, obj, done=None):
    if not isinstance(obj, TupleObject): return False
    if self.elements and obj.elements:
      if len(self.elements) != len(obj.elements): return False
      for (e1,e2) in zip(self.elements, obj.elements):
        if not e1.equal(e2, done): return False
      return True
    if self.elements or obj.elements: return False
    return self.elemall.equal(obj.elemall, done)
  
  def desc1(self, done):
    if self.elements == None:
      return '(%s*)' % self.elemall.desc1(done)
    else:
      return '(%s)' % ','.join( obj.desc1(done) for obj in self.elements )

  def get_element(self, frame, subs, write=False):
    if write:
      frame.raise_expt(TypeErrorType.occur('cannot assign to a tuple.'))
    else:
      frame.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self.elemall


##  TupleType
##
class TupleType(BuiltinSequenceType, BuiltinCallable):
  
  TYPE_NAME = 'tuple'
  TYPE_INSTANCE = TupleObject
  
  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    if args:
      return BuiltinSequenceObject.SequenceConverter(frame, TupleType.create_sequence(), args[0])
    else:
      return TupleType.create_sequence()

  def __init__(self):
    BuiltinCallable.__init__(self, 'tuple', [], [ANY])
    return


##  SetObject
##
class SetObject(BuiltinSequenceObject):

  def desc1(self, done):
    return '([%s])' % self.elemall.desc1(done)

  def copy(self):
    return SetType.create_sequence(elemall=self.elemall)

  def equal(self, obj, done=None):
    if not isinstance(obj, SetObject): return False
    return self.elemall.equal(obj.elemall, done)

  class Intersection(BuiltinConstCallable):
    
    class Mixer(CompoundTypeNode):
      
      def __init__(self, frame, target, src1, src2):
        self.frame = frame
        self.target = target
        self.types1 = CompoundTypeNode()
        self.types2 = CompoundTypeNode()
        CompoundTypeNode.__init__(self)
        src1.connect(self, self.recv1)
        src2.connect(self, self.recv2)
        return
      
      def recv1(self, src):
        for obj in src:
          try:
            obj.get_seq(self).connect(self.types1)
          except NodeTypeError:
            self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
        self.update_intersection()
        return
      
      def recv2(self, src):
        for obj in src:
          try:
            obj.get_seq(self).connect(self.types2)
          except NodeTypeError:
            self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
        self.update_intersection()
        return
        
      def update_intersection(self):
        d = []
        for obj1 in self.types1:
          for obj2 in self.types2:
            if obj1.equal(obj2):
              obj1.connect(self.target.elemall)
        return
      
    def __init__(self, name, src1):
      self.src1 = src1
      BuiltinConstCallable.__init__(self, name, SetType.create_sequence(), [ANY])
      return
    
    def __repr__(self):
      return '%r.intersection' % self.src1
    
    def process_args(self, frame, args, kwargs):
      if kwargs or len(args) != 1:
        return BuiltinConstCallable.process_args(self, frame, args, kwargs)
      self.Mixer(frame, self.retype, self.src1, args[0])
      return self.retype
  
  def get_attr(self, name, write=False):
    if name == 'add':
      return self.SequenceAppender('set.add', self, args=[ANY])
    elif name == 'clear':
      return BuiltinConstCallable('set.clear', NoneType.get_object())
    elif name == 'copy':
      return BuiltinConstCallable('set.copy', self.copy())
    elif name == 'difference':
      return BuiltinConstCallable('set.difference', self.copy(), [[ANY]])
    elif name == 'difference_update':
      return BuiltinConstCallable('set.difference_update', NoneType.get_object(), [[ANY]])
    elif name == 'discard':
      return BuiltinConstCallable('set.discard', NoneType.get_object(), [ANY])
    elif name == 'intersection':
      return SetObject.Intersection('set.intersection', self)
    elif name == 'intersection_update':
      return BuiltinConstCallable('set.intersection_update', NoneType.get_object(), [[ANY]])
    elif name == 'issubset':
      return BuiltinConstCallable('set.issubset', BoolType.get_object(), [[ANY]])
    elif name == 'issuperset':
      return BuiltinConstCallable('set.issuperset', BoolType.get_object(), [[ANY]])
    elif name == 'pop':
      return BuiltinConstCallable('set.pop', NoneType.get_object(), 
                                  expts=[KeyErrorType.maybe('might not able to pop from an empty set.')])
    elif name == 'remove':
      return BuiltinConstCallable('set.remove', NoneType.get_object(), [ANY],
                                  expts=[KeyErrorType.maybe('might not have the value.')])
    elif name == 'symmetric_difference':
      setobj = self.copy()
      return self.SequenceExtender('set.symmetric_difference', setobj, setobj, [ANY])
    elif name == 'symmetric_difference_update':
      return self.SequenceExtender('set.symmetric_difference_update', self, args=[ANY])
    elif name == 'union':
      setobj = self.copy()
      return self.SequenceExtender('set.union', setobj, setobj, [ANY])
    elif name == 'update':
      return self.SequenceExtender('set.update', self, self, [ANY])
    raise NodeAttrError(name)
  

##  SetType
##
class SetType(BuiltinSequenceType, BuiltinCallable):

  TYPE_NAME = 'set'
  TYPE_INSTANCE = SetObject
  
  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    if args:
      return BuiltinSequenceObject.SequenceConverter(frame, SetType.create_sequence(), args[0])
    else:
      return SetType.create_sequence()

  def __init__(self):
    BuiltinCallable.__init__(self, 'set', [], [ANY])
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
      return BuiltinConstCallable('iter.next', self.elemall)
    raise NodeAttrError(name)
  

##  IterType
##
class IterType(BuiltinSequenceType):

  TYPE_NAME = 'iterator'
  TYPE_INSTANCE = IterObject


##  DictObject
##
class DictObject(BuiltinObject):

  # convert
  class DictConverter(CompoundTypeNode):
    
    def __init__(self, frame, dictobj, srcs=[]):
      self.frame = frame
      self.dictobj = dictobj
      CompoundTypeNode.__init__(self, [self.dictobj]+srcs)
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
          elem.connect(self.dictobj.key)
          elem.connect(self.dictobj.value)
          self.frame.raise_expt(TypeErrorType.maybe('might not be able to convert to dict: %s' % obj))
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to dict: %s' % obj))
      return
    
  # fromkeys
  class DictConverterFromKeys(CompoundTypeNode):
    
    def __init__(self, frame, dictobj, srcs=[]):
      self.frame = frame
      self.dictobj = dictobj
      CompoundTypeNode.__init__(self, [self.dictobj]+srcs)
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_seq(self).connect(self.dictobj.key)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to dict: %s' % obj))
      return

  # dict.fromkeys
  class FromKeys(BuiltinConstCallable):
    
    def __init__(self, _, name):
      self.dictobj = DictType.get_dict()
      BuiltinConstCallable.__init__(self, name, self.dictobj, [ANY], [ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      if len(args) < 2:
        NoneType.get_object().connect(self.dictobj.value)
      return BuiltinConstCallable.process_args(self, frame, args, kwargs)
    
    def accept_arg(self, frame, i):
      if i == 0:
        return DictObject.DictConverterFromKeys(frame, self.dictobj)
      else:
        return self.dictobj.value
    
  # dict.get
  class Get(BuiltinConstCallable):
    
    def __init__(self, dictobj, name):
      self.dictobj = dictobj
      self.found = CompoundTypeNode([dictobj.value])
      BuiltinConstCallable.__init__(self, name, self.found, [ANY], [ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      if len(args) == 1:
        self.found.update_types([NoneType.get_object()])
      return BuiltinConstCallable.process_args(self, frame, args, kwargs)
    
    def accept_arg(self, frame, i):
      if i == 0: return None
      return self.found

  # dict.pop
  class Pop(BuiltinConstCallable):
    
    def __init__(self, dictobj, name):
      self.dictobj = dictobj
      self.found = CompoundTypeNode([dictobj.value])
      BuiltinConstCallable.__init__(self, name, self.found, [ANY], [ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      if len(args) == 1:
        frame.raise_expt(KeyErrorType.maybe('might not have the key: %r' % args[0]))
      return BuiltinConstCallable.process_args(self, frame, args, kwargs)
    
    def accept_arg(self, frame, i):
      if i == 0: return None
      return self.found

  # dict.setdefault
  class SetDefault(BuiltinConstCallable):
    
    def __init__(self, dictobj, name):
      self.dictobj = dictobj
      self.found = CompoundTypeNode([dictobj.value])
      BuiltinConstCallable.__init__(self, name, self.found, [ANY], [ANY])
      return
    
    def __repr__(self):
      return '%r.setdefault' % self.dictobj
    
    def process_args(self, frame, args, kwargs):
      if len(args) == 1:
        self.found.update_types([NoneType.get_object()])
      return BuiltinConstCallable.process_args(self, frame, args, kwargs)
    
    def accept_arg(self, frame, i):
      if i == 0:
        return self.dictobj.value
      else:
        return self.found

  # dict.update
  class Update(BuiltinConstCallable):
    
    def __init__(self, dictobj, name):
      self.dictobj = dictobj
      BuiltinConstCallable.__init__(self, name, NoneType.get_object(), [ANY])
      return
    
    def accept_arg(self, frame, _):
      return DictObject.DictConverter(frame, self.dictobj)

  def __init__(self, typeobj, items=None, key=None, value=None):
    if items != None:
      assert key == None and value == None
      self.key = CompoundTypeNode( k for (k,v) in items )
      self.value = CompoundTypeNode( v for (k,v) in items )
    else:
      self.key = CompoundTypeNode(key)
      self.value = CompoundTypeNode(value)
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
    return DictType.get_dict(key=[self.key], value=[self.value])

  def desc1(self, done):
    return '{%s: %s}' % (self.key.desc1(done), self.value.desc1(done))

  def get_attr(self, name, write=False):
    if name == 'clear':
      return BuiltinConstCallable('dict.clear', NoneType.get_object())
    elif name == 'copy':
      return BuiltinConstCallable('dict.copy', self.copy())
    elif name == 'fromkeys':
      return DictObject.FromKeys(self, 'dict.fromkeys')
    elif name == 'get':
      return DictObject.Get(self, 'dict.get')
    elif name == 'has_key':
      return BuiltinConstCallable('dict.has_key', BoolType.get_object(), [ANY])
    elif name == 'items':
      return BuiltinConstCallable('dict.items',
                                  ListType.create_sequence([ TupleType.create_sequence([self.key, self.value]) ]))
    elif name == 'iteritems':
      return BuiltinConstCallable('dict.iteritems',
                                  IterType.create_sequence([ TupleType.create_sequence([self.key, self.value]) ]))
    elif name == 'iterkeys':
      return BuiltinConstCallable('dict.iterkeys',
                                  IterType.create_sequence([ TupleType.create_sequence([self.key]) ]))
    elif name == 'itervalues':
      return BuiltinConstCallable('dict.itervalues',
                                  IterType.create_sequence([ TupleType.create_sequence([self.value]) ]))
    elif name == 'keys':
      return BuiltinConstCallable('dict.keys', ListType.create_sequence([ self.key ]))
    elif name == 'pop':
      return DictObject.Pop(self, 'dict.pop')
    elif name == 'popitem':
      return BuiltinConstCallable('dict.popitem', TupleType.create_sequence([self.key, self.value]),
                                  expts=[KeyErrorType.maybe('might not able to pop from an empty dict.')])
    elif name == 'setdefault':
      return DictObject.SetDefault(self, 'dict.setdefault')
    elif name == 'update':
      return DictObject.Update(self, 'dict.update')
    elif name == 'values':
      return BuiltinConstCallable('dict.values', ListType.create_sequence([ self.value ]))
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
    return IterType.create_sequence(elemall=self.key)


##  DictType
##
class DictType(BuiltinType, BuiltinCallable):
  
  TYPE_NAME = 'dict'
  TYPE_INSTANCE = DictObject
  
  def process_args(self, frame, args, kwargs):
    if kwargs:
      return DictType.get_dict(key=[StrType.get_object()], value=kwargs.values())
    if args:
      return DictObject.DictConverter(frame, DictType.get_dict(), [args[0]])
    else:
      return DictType.get_dict()

  def __init__(self):
    BuiltinCallable.__init__(self, 'dict', [], [ANY])
    return

  @classmethod
  def create_dict(klass, items=None, key=None, value=None):
    return DictObject(klass.get_typeobj(), items=items, key=key, value=value)
