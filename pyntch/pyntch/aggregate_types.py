#!/usr/bin/env python
from typenode import CompoundTypeNode, NodeTypeError, NodeAttrError, \
     BuiltinType, BuiltinObject
from exception import TypeChecker, \
     TypeErrorType, IndexErrorType, ValueErrorType, KeyErrorType, StopIterationType
from basic_types import BuiltinCallable, BuiltinConstMethod, BoolType, IntType, StrType, NoneType, ANY
from expression import IterElement


##  BuiltinAggregateObject
##
class BuiltinAggregateObject(BuiltinObject):

  def __init__(self, typeobj):
    self.attrs = {}
    BuiltinObject.__init__(self, typeobj)
    return
  
  def get_attr(self, name, write=False):
    if write: raise NodeAttrError(name)
    if name in self.attrs:
      attr = self.attrs[name]
    else:
      attr = self.create_attr(name)
      self.attrs[name] = attr
    return attr

  def signature(self):
    return self.get_type()


##  BuiltinAggregateType
##
class BuiltinAggregateType(BuiltinCallable, BuiltinType):

  def __init__(self):
    self.cache = {}
    self.nullobj = None
    BuiltinType.__init__(self)
    BuiltinCallable.__init__(self, self.TYPE_NAME, [], [ANY])
    return

  def get_converted(self, frame, node):
    if node in self.cache:
      obj = self.cache[node]
    else:
      obj = self.create_sequence(frame, node)
      self.cache[node] = obj
    return obj

  def get_null(self):
    if not self.nullobj:
      self.nullobj = self.create_null()
    return self.nullobj
  
  def create_sequence(self, frame, node):
    raise NotImplementedError


##  BuiltinSequenceObject
##
class BuiltinSequenceObject(BuiltinAggregateObject):

  # SequenceExtender
  class SequenceExtender(BuiltinConstMethod):
    
    def __init__(self, name, target, retobj=NoneType.get_object(), args=None, optargs=None):
      self.target = target
      BuiltinConstMethod.__init__(self, name, retobj, args=args, optargs=optargs)
      return
    
    def __repr__(self):
      return '%r.extend' % self.target
    
    def accept_arg(self, frame, i, arg1):
      IterElement(frame, arg1).connect(self.target.elemall)
      return

  # SequenceAppender
  class SequenceAppender(BuiltinConstMethod):
    
    def __init__(self, name, target, retobj=NoneType.get_object(), args=None, optargs=None):
      self.target = target
      BuiltinConstMethod.__init__(self, name, retobj, args=args, optargs=optargs)
      return
    
    def __repr__(self):
      return '%r.append' % self.target
    
    def accept_arg(self, frame, i, arg1):
      arg1.connect(self.target.elemall)
      return

  # BuiltinSequenceObject
  def __init__(self, typeobj, elemall=None):
    self.elemall = elemall or CompoundTypeNode()
    self.iter = None
    BuiltinAggregateObject.__init__(self, typeobj)
    return
  
  def get_iter(self, frame):
    if not self.iter:
      self.iter = IterType.create_iter(self.elemall)
    return self.iter

  def connect_element(self, seqobj):
    assert isinstance(seqobj, BuiltinSequenceObject)
    self.elemall.connect(seqobj.elemall)
    return

##  BuiltinSequenceType
##
class BuiltinSequenceType(BuiltinAggregateType):
  
  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    if args:
      return self.get_converted(frame, args[0])
    return self.get_null()


##  List
##
class ListObject(BuiltinSequenceObject):

  # InsertMethod
  class InsertMethod(BuiltinSequenceObject.SequenceAppender):
    
    def accept_arg(self, frame, i, arg1):
      if i == 0:
        BuiltinConstMethod.accept_arg(self, frame, i, arg1)
      else:
        BuiltinSequenceObject.SequenceAppender.accept_arg(self, frame, i, arg1)
      return

  # SortMethod
  class SortMethod(BuiltinConstMethod):
    
    class FuncChecker(CompoundTypeNode):
      
      def __init__(self, frame, target, fcmp, fkey):
        self.frame = frame
        self.target = target
        self.key = CompoundTypeNode()
        CompoundTypeNode.__init__(self)
        if fkey:
          fkey.connect(self.recv_fkey)
        else:
          target.elemall.connect(self.key)
        if fcmp:
          fcmp.connect(self.recv_fcmp)
        return
      
      def recv_fkey(self, src):
        for obj in src:
          try:
            obj.call(self.frame, [self.target.elemall], {}, None, None).connect(self.key)
          except NodeTypeError:
            self.frame.raise_expt(TypeErrorType.occur('key function not callable:' % obj))
        return
      
      def recv_fcmp(self, src):
        for obj in src:
          try:
            tc = TypeChecker(self.frame, IntType.get_typeobj(),
                             'the return value of comparison function')
            obj.call(self.frame, [self.key, self.key], {}, None, None).connect(tc)
          except NodeTypeError:
            self.frame.raise_expt(TypeErrorType.occur('cmp function not callable:' % obj))
        return

    def __init__(self, name, target):
      self.target = target
      BuiltinConstMethod.__init__(self, name, NoneType.get_object(), [], [ANY,ANY,ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      params = dict.fromkeys(['cmp', 'key', 'reverse'])
      args = list(args)
      if args:
        params['cmp'] = args.pop(0)
      if args:
        params['key'] = args.pop(0)
      if args:
        params['reserved'] = args.pop(0)
      for (k,v) in kwargs.iteritems():
        if k in params:
          if params[k] != None:
            frame.raise_expt(TypeErrorType.occur('%s: keyword %r was already given' % (self.name, k)))
          else:
            params[k] = v
        else:
          frame.raise_expt(TypeErrorType.occur('%s cannot take keyword: %s' % (self.name, k)))
      self.FuncChecker(frame, self.target, params['cmp'], params['key'])
      return NoneType.get_object()

  # ListObject
  def desc1(self, done):
    return '[%s]' % self.elemall.desc1(done)

  def get_element(self, frame, subs, write=False):
    frame.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self.elemall

  def create_attr(self, name):
    if name == 'append':
      return self.SequenceAppender('list.append', self, args=[ANY])
    elif name == 'count':
      return BuiltinConstMethod('list.count', IntType.get_object(), [ANY])
    elif name == 'extend':
      return self.SequenceExtender('list.extend', self, args=[ANY])
    elif name == 'index':
      return BuiltinConstMethod('list.index', IntType.get_object(), [ANY], [IntType, IntType],
                                  expts=[ValueErrorType.maybe('might not able to find the element.')])
    elif name == 'insert':
      return self.InsertMethod('list.insert', self, [IntType, ANY])
    elif name == 'pop':
      return BuiltinConstMethod('list.pop', self.elemall, [], [IntType],
                                  expts=[ValueErrorType.maybe('might be empty list or out of range.')])
    elif name == 'remove':
      return BuiltinConstMethod('list.remove', NoneType.get_object(), [ANY],
                                  expts=[ValueErrorType.maybe('might not able to remove the element.')])
    elif name == 'reverse':
      return BuiltinConstMethod('list.remove', NoneType.get_object())
    elif name == 'sort':
      return self.SortMethod('list.sort', self)
    raise NodeAttrError(name)


##  ListType
##
class ListType(BuiltinSequenceType):
  
  TYPE_NAME = 'list'
  
  @classmethod
  def create_list(klass, elemall=None):
    return ListObject(klass.get_typeobj(), elemall=elemall)

  def create_sequence(self, frame, node):
    listobj = ListType.create_list()
    IterElement(frame, node).connect(listobj.elemall)
    return listobj

  def create_null(self):
    return ListType.create_list()

  
##  TupleObject
##
class TupleObject(BuiltinSequenceObject):
  
  def __init__(self, typeobj, elements=None, elemall=None):
    self.elements = elements
    if elements != None:
      elemall = CompoundTypeNode(elements)
    BuiltinSequenceObject.__init__(self, typeobj, elemall)
    return

  def __repr__(self):
    if self.elements == None:
      return '(*%s)' % self.elemall.describe()
    else:
      return '(%s)' % ','.join( obj.describe() for obj in self.elements )

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

  def create_attr(self, name):
    raise NodeAttrError(name)


##  TupleType
##
class TupleType(BuiltinSequenceType):
  
  TYPE_NAME = 'tuple'
    
  @classmethod
  def create_tuple(klass, elements=None, elemall=None):
    return TupleObject(klass.get_typeobj(), elements=elements, elemall=elemall)

  def create_sequence(self, frame, node):
    tupleobj = TupleType.create_tuple()
    IterElement(frame, node).connect(tupleobj.elemall)
    return tupleobj
  
  def create_null(self):
    return TupleType.create_tuple()


##  SetObject
##
class SetObject(BuiltinSequenceObject):

  # Intersection
  class Intersection(BuiltinConstMethod):
    
    class TypeMixer(CompoundTypeNode):
      
      def __init__(self, frame, target, src1, src2):
        self.frame = frame
        self.target = target
        self.types1 = CompoundTypeNode()
        self.types2 = CompoundTypeNode()
        CompoundTypeNode.__init__(self)
        src1.connect(self.recv1)
        src2.connect(self.recv2)
        return
      
      def recv1(self, src):
        for obj in src:
          IterElement(self.frame, obj).connect(self.types1)
        self.update_intersection()
        return
      
      def recv2(self, src):
        for obj in src:
          IterElement(self.frame, obj).connect(self.types2)
        self.update_intersection()
        return
        
      def update_intersection(self):
        for obj1 in self.types1:
          for obj2 in self.types2:
            if obj1.get_type() == obj2.get_type():
              obj1.connect(self.target.elemall)
              obj2.connect(self.target.elemall)
        return
      
    def __init__(self, name, src1):
      self.src1 = src1
      BuiltinConstMethod.__init__(self, name, SetType.create_set(), [ANY])
      return
    
    def __repr__(self):
      return '%r.intersection' % self.src1
    
    def process_args(self, frame, args, kwargs):
      if kwargs or len(args) != 1:
        return BuiltinConstMethod.process_args(self, frame, args, kwargs)
      self.TypeMixer(frame, self.retobj, self.src1, args[0])
      return self.retobj

  def desc1(self, done):
    return '([%s])' % self.elemall.desc1(done)

  def copy(self):
    return SetType.create_set(self.elemall)
  
  def create_attr(self, name):
    if name == 'add':
      return self.SequenceAppender('set.add', self, args=[ANY])
    elif name == 'clear':
      return BuiltinConstMethod('set.clear', NoneType.get_object())
    elif name == 'copy':
      return BuiltinConstMethod('set.copy', self.copy())
    elif name == 'difference':
      return BuiltinConstMethod('set.difference', self.copy(), [[ANY]])
    elif name == 'difference_update':
      return BuiltinConstMethod('set.difference_update', NoneType.get_object(), [[ANY]])
    elif name == 'discard':
      return BuiltinConstMethod('set.discard', NoneType.get_object(), [ANY])
    elif name == 'intersection':
      return SetObject.Intersection('set.intersection', self)
    elif name == 'intersection_update':
      return BuiltinConstMethod('set.intersection_update', NoneType.get_object(), [[ANY]])
    elif name == 'issubset':
      return BuiltinConstMethod('set.issubset', BoolType.get_object(), [[ANY]])
    elif name == 'issuperset':
      return BuiltinConstMethod('set.issuperset', BoolType.get_object(), [[ANY]])
    elif name == 'pop':
      return BuiltinConstMethod('set.pop', NoneType.get_object(), 
                                  expts=[KeyErrorType.maybe('might not able to pop from an empty set.')])
    elif name == 'remove':
      return BuiltinConstMethod('set.remove', NoneType.get_object(), [ANY],
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
class SetType(BuiltinSequenceType):

  TYPE_NAME = 'set'

  @classmethod
  def create_set(klass, elemall=None):
    return SetObject(klass.get_typeobj(), elemall=elemall)

  def create_sequence(self, frame, node):
    setobj = SetType.create_set()
    IterElement(frame, node).connect(setobj.elemall)
    return setobj

  def create_null(self):
    return SetType.create_set()


##  IterObject
##
class IterObject(BuiltinSequenceObject):
  
  def __repr__(self):
    return '(%s, ...)' % self.elemall

  def desc1(self, done):
    return '(%s, ...)' % self.elemall.desc1(done)

  def get_iter(self, frame):
    return self

  def create_attr(self, name):
    if name == 'next':
      return BuiltinConstMethod('iter.next', self.elemall,
                                  expts=[StopIterationType.maybe('might raise StopIteration')])
    raise NodeAttrError(name)
  

##  IterType
##
class IterType(BuiltinType):

  TYPE_NAME = 'iterator'

  @classmethod
  def create_iter(klass, elemall=None):
    return IterObject(klass.get_typeobj(), elemall=elemall)


##  GeneratorObject
##
class GeneratorSlot(CompoundTypeNode):
  
  def __init__(self, value):
    self.sent = CompoundTypeNode()
    CompoundTypeNode.__init__(self, [value])
    return

class GeneratorObject(IterObject):

  # Send
  class Send(BuiltinConstMethod):
    
    def __init__(self, name, target, retobj=NoneType.get_object(), args=None, expts=None):
      self.target = target
      BuiltinConstMethod.__init__(self, name, retobj, args=args, expts=expts)
      return
    
    def accept_arg(self, frame, i, arg1):
      arg1.connect(self.target.sent)
      return

  # GeneratorObject
  def __init__(self, typeobj, elemall=None, elements=None):
    self.sent = CompoundTypeNode()
    if elements:
      for obj in elements:
        if isinstance(obj, GeneratorSlot):
          self.sent.connect(obj.sent)
    IterObject.__init__(self, typeobj, elemall=elemall)
    return

  def create_attr(self, name):
    if name == 'send':
      return self.Send('generator.send', self, self.elemall, [ANY],
                       expts=[StopIterationType.maybe('might raise StopIteration')])
    if name == 'next':
      NoneType.get_object().connect(self.sent)
      return self.Send('generator.next', self, self.elemall,
                       expts=[StopIterationType.maybe('might raise StopIteration')])
    if name == 'throw':
      # XXX do nothing for now
      return BuiltinConstMethod('generator.throw', NoneType.get_object(), [ANY], [ANY, ANY])
    if name == 'close':
      return self.Send('generator.close', self, NoneType.get_object(), [ANY])
    return IterObject.create_attr(self, name)


##  GeneratorType
##
class GeneratorType(IterType):

  TYPE_NAME = 'generator'

  @classmethod
  def create_slot(klass, value):
    return GeneratorSlot(value)

  @classmethod
  def create_generator(klass, elements):
    return GeneratorObject(klass.get_typeobj(), elements=elements)


##  DictObject
##
class DictObject(BuiltinAggregateObject):

  # convert
  class DictConverter(CompoundTypeNode):
    
    def __init__(self, frame, target):
      self.frame = frame
      self.target = target
      CompoundTypeNode.__init__(self)
      return
    
    def __repr__(self):
      return 'convert(%r)' % self.target
    
    def recv(self, src):
      for obj in src:
        IterElement(self.frame, obj).connect(self.recv_pair)
      return
  
    def recv_pair(self, src):
      for obj in src:
        if obj.is_type(TupleType.get_typeobj()) and obj.elements:
          if len(obj.elements) == 2:
            (k,v) = obj.elements
            k.connect(self.target.key)
            v.connect(self.target.value)
          else:
            self.frame.raise_expt(TypeErrorType.occur('cannot convert to dict: tuple length is not 2: %s' % obj))
          continue
        elem = IterElement(self.frame, obj)
        elem.connect(self.target.key)
        elem.connect(self.target.value)
        self.frame.raise_expt(TypeErrorType.maybe('might not be able to convert to dict: %s' % obj))
      return
    
  # fromkeys
  class DictConverterFromKeys(CompoundTypeNode):
    
    def __init__(self, frame, target):
      self.frame = frame
      self.target = target
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      for obj in src:
        IterElement(self.frame, obj).connect(self.target.key)
      return

  # dict.fromkeys
  class FromKeys(BuiltinConstMethod):
    
    def __init__(self, _, name):
      self.cache = {}
      self.dictobj = DictType.create_dict()
      BuiltinConstMethod.__init__(self, name, self.dictobj, [ANY], [ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      if 2 <= len(args):
        args[1].connect(self.dictobj.value)
      else:
        NoneType.get_object().connect(self.dictobj.value)
      v = args[0]
      if v not in self.cache:
        converter = DictObject.DictConverterFromKeys(frame, self.dictobj)
        self.cache[v] = converter
        v.connect(converter)
      return self.dictobj
    
  # dict.get
  class Get(BuiltinConstMethod):
    
    def __init__(self, dictobj, name):
      self.dictobj = dictobj
      self.found = CompoundTypeNode([dictobj.value])
      BuiltinConstMethod.__init__(self, name, self.found, [ANY], [ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      if len(args) == 1:
        self.found.update_type(NoneType.get_object())
      return BuiltinConstMethod.process_args(self, frame, args, kwargs)
    
    def accept_arg(self, frame, i, arg1):
      if i != 0:
        arg1.connect(self.found)
      return

  # dict.pop
  class Pop(BuiltinConstMethod):
    
    def __init__(self, dictobj, name):
      self.dictobj = dictobj
      self.found = CompoundTypeNode([dictobj.value])
      BuiltinConstMethod.__init__(self, name, self.found, [ANY], [ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      if len(args) == 1:
        frame.raise_expt(KeyErrorType.maybe('might not have the key: %r' % args[0]))
      return BuiltinConstMethod.process_args(self, frame, args, kwargs)
    
    def accept_arg(self, frame, i, arg1):
      if i != 0:
        arg1.connect(self.found)
      return

  # dict.setdefault
  class SetDefault(BuiltinConstMethod):
    
    def __init__(self, dictobj, name):
      self.dictobj = dictobj
      self.found = CompoundTypeNode([dictobj.value])
      BuiltinConstMethod.__init__(self, name, self.found, [ANY], [ANY])
      return
    
    def __repr__(self):
      return '%r.setdefault' % self.dictobj
    
    def process_args(self, frame, args, kwargs):
      if len(args) == 1:
        self.found.update_type(NoneType.get_object())
      return BuiltinConstMethod.process_args(self, frame, args, kwargs)
    
    def accept_arg(self, frame, i, arg1):
      if i == 0:
        arg1.connect(self.dictobj.value)
      else:
        arg1.connect(self.found)
      return

  # dict.update
  class Update(BuiltinConstMethod):
    
    def __init__(self, dictobj, name):
      self.cache = {}
      self.dictobj = dictobj
      BuiltinConstMethod.__init__(self, name, NoneType.get_object(), [ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      v = args[0]
      if v not in self.cache:
        converter = DictObject.DictConverterFromKeys(frame, self.dictobj)
        self.cache[v] = converter
        v.connect(converter)
      return NoneType.get_object()

  # DictObject
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
    self.iter = None
    BuiltinAggregateObject.__init__(self, typeobj)
    return
  
  def __repr__(self):
    return '{%s: %s}' % (self.key, self.value)

  def copy(self):
    return DictType.create_dict(key=[self.key], value=[self.value])

  def desc1(self, done):
    return '{%s: %s}' % (self.key.desc1(done), self.value.desc1(done))

  def create_attr(self, name):
    if name == 'clear':
      return BuiltinConstMethod('dict.clear', NoneType.get_object())
    elif name == 'copy':
      return BuiltinConstMethod('dict.copy', self.copy())
    elif name == 'fromkeys':
      return DictObject.FromKeys(self, 'dict.fromkeys')
    elif name == 'get':
      return DictObject.Get(self, 'dict.get')
    elif name == 'has_key':
      return BuiltinConstMethod('dict.has_key', BoolType.get_object(), [ANY])
    elif name == 'keys':
      return BuiltinConstMethod('dict.keys',
                                  ListType.create_list(self.key))
    elif name == 'values':
      return BuiltinConstMethod('dict.values',
                                  ListType.create_list(self.value))
    elif name == 'items':
      return BuiltinConstMethod('dict.items',
                                  ListType.create_list(TupleType.create_tuple([self.key, self.value])))
    elif name == 'iterkeys':
      return BuiltinConstMethod('dict.iterkeys',
                                  IterType.create_iter(self.key))
    elif name == 'itervalues':
      return BuiltinConstMethod('dict.itervalues',
                                  IterType.create_iter(self.value))
    elif name == 'iteritems':
      return BuiltinConstMethod('dict.iteritems',
                                  IterType.create_iter(TupleType.create_tuple([self.key, self.value])))
    elif name == 'pop':
      return DictObject.Pop(self, 'dict.pop')
    elif name == 'popitem':
      return BuiltinConstMethod('dict.popitem', TupleType.create_tuple([self.key, self.value]),
                                  expts=[KeyErrorType.maybe('might not able to pop from an empty dict.')])
    elif name == 'setdefault':
      return DictObject.SetDefault(self, 'dict.setdefault')
    elif name == 'update':
      return DictObject.Update(self, 'dict.update')
    raise NodeAttrError(name)

  def get_element(self, frame, subs, write=False):
    key = subs[0]
    if write:
      key.connect(self.key)
    else:
      frame.raise_expt(KeyErrorType.maybe('might not have the key: %r' % key))
    return self.value

  def get_iter(self, frame):
    if not self.iter:
      self.iter = IterType.create_iter(self.key)
    return self.iter


##  DictType
##
class DictType(BuiltinAggregateType):
  
  TYPE_NAME = 'dict'

  @classmethod
  def create_dict(klass, items=None, key=None, value=None):
    return DictObject(klass.get_typeobj(), items=items, key=key, value=value)

  def process_args(self, frame, args, kwargs):
    if kwargs:
      node = tuple(kwargs.values())
      if node in self.cache:
        obj = self.cache[node]
      else:
        obj = DictType.create_dict(key=[StrType.get_object()], value=kwargs.values())
        self.cache[node] = obj
      return obj
    if args:
      return self.get_converted(frame, args[0])
    return self.get_null()

  def create_sequence(self, frame, node):
    dictobj = DictType.create_dict()
    node.connect(DictObject.DictConverter(frame, dictobj))
    return dictobj

  def create_null(self):
    return DictType.create_dict()


##  EnumerateType
##
class EnumerateType(BuiltinCallable, BuiltinType):

  def __init__(self):
    BuiltinType.__init__(self)
    BuiltinCallable.__init__(self, 'enumerate', [ANY])
    return

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    elemall = TupleType.create_tuple([IntType.get_object(), IterElement(frame, args[0])])
    return IterObject(self.get_typeobj(), elemall=elemall)
