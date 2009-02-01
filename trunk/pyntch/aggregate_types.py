#!/usr/bin/env python
from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, \
     BuiltinType, BuiltinObject
from exception import TypeChecker, \
     TypeErrorType, IndexErrorType, ValueErrorType, KeyErrorType, StopIterationType
from basic_types import BuiltinCallable, BuiltinConstCallable, BoolType, IntType, StrType, NoneType, ANY


##  Aggregate Types
##
class BuiltinSequenceType(BuiltinType):
  
  @classmethod
  def create_sequence(klass, elemall=None):
    return klass.TYPE_INSTANCE(klass.get_typeobj(), elemall=elemall)


##  BuiltinSequenceObject
##
class BuiltinSequenceObject(BuiltinObject):

  def expand(self, nodes, done):
    if self in done: return
    done.add(self)
    for obj in self.elemall.types:
      if isinstance(obj, self.__class__):
        obj.expand(nodes, done)
      else:
        nodes.add(obj)
    return
  
  class SequenceConverter(CompoundTypeNode):
    def __init__(self, frame, target, src):
      self.frame = frame
      self.target = target
      CompoundTypeNode.__init__(self, [src])
      return
    def __repr__(self):
      return 'convert(%r)' % self.target
    def recv(self, src):
      for obj in src:
        try:
          obj.get_seq(self.frame).connect(self.target.elemall)
        except (NodeTypeError, NodeAttrError):
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
            obj.get_seq(self.frame).connect(self.target.elemall)
          except (NodeTypeError, NodeAttrError):
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

  def __init__(self, typeobj, elemall=None):
    self.elemall = elemall or CompoundTypeNode()
    BuiltinObject.__init__(self, typeobj)
    return

  def get_iter(self, frame):
    return IterType.create_iter(self.elemall)


##  List
##
class ListObject(BuiltinSequenceObject):

  ##  Methods
  ##
  class InsertMethod(BuiltinSequenceObject.SequenceAppender):
    def accept_arg(self, frame, i):
      if i == 0:
        return BuiltinConstCallable.accept_arg(self, frame, i)
      return BuiltinSequenceObject.SequenceAppender.accept_arg(self, frame, i)
      
  class SortMethod(BuiltinConstCallable):
    class Processor(CompoundTypeNode):
      def __init__(self, frame, target, fcmp, fkey):
        self.frame = frame
        self.target = target
        self.key = CompoundTypeNode()
        if fkey:
          fkey.connect(self, self.recv_fkey)
        else:
          target.elemall.connect(self.key)
        if fcmp:
          fcmp.connect(self, self.recv_fcmp)
        CompoundTypeNode.__init__(self)
        return
      def recv_fkey(self, src):
        for obj in src:
          try:
            obj.call(self.frame, [self.target.elemall], {}).connect(self.key)
          except NodeTypeError:
            frame.raise_expt(TypeErrorType.occur('key function not callable:' % obj))
        return
      def recv_fcmp(self, src):
        for obj in src:
          try:
            tc = TypeChecker(self.frame, IntType.get_typeobj(),
                             'the return value of comparison function')
            obj.call(self.frame, [self.key, self.key], {}).connect(tc)
          except NodeTypeError:
            frame.raise_expt(TypeErrorType.occur('cmp function not callable:' % obj))
        return

    def __init__(self, name, target):
      self.target = target
      BuiltinConstCallable.__init__(self, name, NoneType.get_object(), [], [ANY,ANY,ANY])
      return
    def process_args(self, frame, args, kwargs):
      params = dict.fromkeys(['cmp', 'key', 'reverse'])
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
      return self.Processor(frame, self.target, params['cmp'], params['key'])

  def desc1(self, done):
    return '[%s]' % self.elemall.desc1(done)

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
      return self.SortMethod('list.sort', self)
    raise NodeAttrError(name)

  def get_element(self, frame, subs, write=False):
    frame.raise_expt(IndexErrorType.maybe('%r index might be out of range.' % self))
    return self.elemall

    
##  ListType
##
class ListType(BuiltinSequenceType, BuiltinCallable):
  
  TYPE_NAME = 'list'
  TYPE_INSTANCE = ListObject
  CACHE = {}
  
  @classmethod
  def concat(klass, obj1, obj2):
    return klass.create_sequence(CompoundTypeNode([obj1.elemall, obj2.elemall]))

  @classmethod
  def multiply(klass, obj):
    return obj
    
  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    if args:
      listobj = ListType.create_sequence()
      BuiltinSequenceObject.SequenceConverter(frame, listobj, args[0])
      return listobj
    else:
      return ListType.create_sequence()

  def __init__(self):
    BuiltinCallable.__init__(self, 'list', [], [ANY])
    return

  
##  TupleObject
##
class TupleObject(BuiltinSequenceObject):
  
  def __init__(self, typeobj, elemall=None, elements=None):
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

  @classmethod
  def create_tuple(klass, elements):
    return klass.TYPE_INSTANCE(klass.get_typeobj(), elements=elements)
  
  @classmethod
  def concat(klass, obj1, obj2):
    return klass.create_sequence(CompoundTypeNode([obj1.elemall, obj2.elemall]))

  @classmethod
  def multiply(klass, obj):
    return klass.create_sequence(obj.elemall)

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('%s cannot take a keyword argument' % (self.name)))
      return UndefinedTypeNode()
    if args:
      tupleobj = TupleType.create_sequence()
      BuiltinSequenceObject.SequenceConverter(frame, tupleobj, args[0])
      return tupleobj
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
    return SetType.create_sequence(self.elemall)

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
            obj.get_seq(self.frame).connect(self.types1)
          except (NodeTypeError, NodeAttrError):
            self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
        self.update_intersection()
        return
      
      def recv2(self, src):
        for obj in src:
          try:
            obj.get_seq(self.frame).connect(self.types2)
          except (NodeTypeError, NodeAttrError):
            self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
        self.update_intersection()
        return
        
      def update_intersection(self):
        XXX
        d = []
        for obj1 in self.types1:
          for obj2 in self.types2:
            if obj1.signature() == obj2.signature():
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
      setobj = SetType.create_sequence()
      BuiltinSequenceObject.SequenceConverter(frame, setobj, args[0])
      return setobj
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
      return BuiltinConstCallable('iter.next', self.elemall,
                                  expts=[StopIterationType.maybe('might raise StopIteration')])
    raise NodeAttrError(name)
  

##  IterType
##
class IterType(BuiltinSequenceType):

  TYPE_NAME = 'iterator'
  TYPE_INSTANCE = IterObject

  @classmethod
  def create_sequence(klass, elemall=None):
    raise NodeTypeError('not sequence type')

  @classmethod
  def create_iter(klass, elemall=None):
    return klass.TYPE_INSTANCE(klass.get_typeobj(), elemall=elemall)


##  GeneratorObject
##
class GeneratorSlot(CompoundTypeNode):
  
  def __init__(self, value):
    self.sent = CompoundTypeNode()
    CompoundTypeNode.__init__(self, [value])
    return

class GeneratorObject(IterObject):
  
  def __init__(self, typeobj, elemall=None, elements=None):
    self.sent = CompoundTypeNode()
    if elements:
      for obj in elements:
        if isinstance(obj, GeneratorSlot):
          self.sent.connect(obj.sent)
    IterObject.__init__(self, typeobj, elemall=elemall)
    return

  class Send(BuiltinConstCallable):
    
    def __init__(self, name, target, retype=NoneType.get_object(), args=None, expts=None):
      self.target = target
      BuiltinConstCallable.__init__(self, name, retype, args=args, expts=expts)
      return
    
    def accept_arg(self, frame, _):
      return self.target.sent

  def get_attr(self, name, write=False):
    if name == 'send':
      return self.Send('generator.send', self, self.elemall, [ANY],
                       expts=[StopIterationType.maybe('might raise StopIteration')])
    if name == 'next':
      NoneType.get_object().connect(self.sent)
      return self.Send('generator.next', self, self.elemall,
                       expts=[StopIterationType.maybe('might raise StopIteration')])
    if name == 'throw':
      # XXX do nothing
      return BuiltinConstCallable('generator.throw', NoneType.get_object(), [ANY], [ANY, ANY])
    if name == 'close':
      return self.Send('generator.close', self, NoneType.get_object(), [ANY])
    return IterObject.get_attr(self, name, write=write)


##  GeneratorType
##
class GeneratorType(IterType):

  TYPE_NAME = 'generator'
  TYPE_INSTANCE = GeneratorObject

  @classmethod
  def create_slot(klass, value):
    return GeneratorSlot(value)

  @classmethod
  def create_generator(klass, elements):
    return klass.TYPE_INSTANCE(klass.get_typeobj(), elements=elements)


##  DictObject
##
class DictObject(BuiltinObject):

  # convert
  class DictConverter(CompoundTypeNode):
    
    def __init__(self, frame, dictobj, src):
      self.frame = frame
      self.dictobj = dictobj
      CompoundTypeNode.__init__(self, [src])
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_seq(self.frame).connect(self, self.recv_pair)
        except (NodeTypeError, NodeAttrError):
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
          elem = obj.get_seq(self.frame)
          elem.connect(self.dictobj.key)
          elem.connect(self.dictobj.value)
          self.frame.raise_expt(TypeErrorType.maybe('might not be able to convert to dict: %s' % obj))
        except (NodeTypeError, NodeAttrError):
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to dict: %s' % obj))
      return
    
  # fromkeys
  class DictConverterFromKeys(CompoundTypeNode):
    
    def __init__(self, frame, dictobj, src):
      self.frame = frame
      self.dictobj = dictobj
      CompoundTypeNode.__init__(self, [src])
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_seq(self.frame).connect(self.dictobj.key)
        except (NodeTypeError, NodeAttrError):
          self.frame.raise_expt(TypeErrorType.occur('cannot convert to dict: %s' % obj))
      return

  # dict.fromkeys
  class FromKeys(BuiltinConstCallable):
    
    def __init__(self, _, name):
      self.dictobj = DictType.create_dict()
      BuiltinConstCallable.__init__(self, name, self.dictobj, [ANY], [ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      if 2 <= len(args):
        args[1].connect(self.dictobj.value)
      else:
        NoneType.get_object().connect(self.dictobj.value)
      DictObject.DictConverterFromKeys(frame, self.dictobj, args[0])
      return self.dictobj
    
  # dict.get
  class Get(BuiltinConstCallable):
    
    def __init__(self, dictobj, name):
      self.dictobj = dictobj
      self.found = CompoundTypeNode([dictobj.value])
      BuiltinConstCallable.__init__(self, name, self.found, [ANY], [ANY])
      return
    
    def process_args(self, frame, args, kwargs):
      if len(args) == 1:
        self.found.update_type(NoneType.get_object())
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
        self.found.update_type(NoneType.get_object())
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
    
    def process_args(self, frame, args, kwargs):
      DictObject.DictConverterFromKeys(frame, self.dictobj, args[0])
      return self.dictobj

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

  def copy(self):
    return DictType.create_dict(key=[self.key], value=[self.value])

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
    elif name == 'keys':
      return BuiltinConstCallable('dict.keys',
                                  ListType.create_sequence(self.key))
    elif name == 'values':
      return BuiltinConstCallable('dict.values',
                                  ListType.create_sequence(self.value))
    elif name == 'items':
      return BuiltinConstCallable('dict.items',
                                  ListType.create_sequence(TupleType.create_tuple([self.key, self.value])))
    elif name == 'iterkeys':
      return BuiltinConstCallable('dict.iterkeys',
                                  IterType.create_iter(self.key))
    elif name == 'itervalues':
      return BuiltinConstCallable('dict.itervalues',
                                  IterType.create_iter(self.value))
    elif name == 'iteritems':
      return BuiltinConstCallable('dict.iteritems',
                                  IterType.create_iter(TupleType.create_tuple([self.key, self.value])))
    elif name == 'pop':
      return DictObject.Pop(self, 'dict.pop')
    elif name == 'popitem':
      return BuiltinConstCallable('dict.popitem', TupleType.create_tuple([self.key, self.value]),
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
    return IterType.create_iter(self.key)


##  DictType
##
class DictType(BuiltinType, BuiltinCallable):
  
  TYPE_NAME = 'dict'
  TYPE_INSTANCE = DictObject
  
  def process_args(self, frame, args, kwargs):
    if kwargs:
      return DictType.create_dict(key=[StrType.get_object()], value=kwargs.values())
    if args:
      dictobj = DictType.create_dict()
      DictObject.DictConverter(frame, dictobj, args[0])
      return dictobj
    else:
      return DictType.create_dict()

  def __init__(self):
    BuiltinCallable.__init__(self, 'dict', [], [ANY])
    return

  @classmethod
  def create_dict(klass, items=None, key=None, value=None):
    return DictObject(klass.get_typeobj(), items=items, key=key, value=value)
