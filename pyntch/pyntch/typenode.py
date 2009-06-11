#!/usr/bin/env python
##
##  typenode.py
##

import sys

class NodeError(Exception): pass
class NodeTypeError(NodeError): pass
class NodeAttrError(NodeError): pass
class NodeAssignError(NodeError): pass


##  TypeNode
##
##  A TypeNode object represents a place where a potential
##  data could be stored or passed in the course of execution of
##  the whole program. The data once stored in a node can be propagated to
##  other nodes via one or multiple outbound links.
##
class TypeNode(object):

  verbose = 0
  debug = 0
  N = 0

  @classmethod
  def inc(klass):
    if not klass.verbose: return
    klass.N += 1
    if klass.N % 1000 == 0:
      sys.stderr.write('.'); sys.stderr.flush()
    return
  
  @classmethod  
  def showstat(klass):
    if not klass.verbose: return
    print >>sys.stderr, '%d nodes' % klass.N
    return

  def __init__(self, types):
    self.types = set(types)
    self.sendto = []
    TypeNode.inc()
    return

  def __iter__(self):
    return iter(list(self.types))

  # connect(receiver): connects this node to
  # another node and designates that any data stored at
  # this node be propagated to the other node(s).
  # The receiver parameter is either CompoundTypeNode object or
  # a function object that receives a value every time it changed.
  def connect(self, receiver):
    assert callable(receiver)
    if self.debug:
      print >>sys.stderr, 'connect: %r -> %r' % (self, receiver)
    if receiver in self.sendto: return False
    self.sendto.append(receiver)
    return receiver(self)

  def get_attr(self, frame, anchor, name, write=False):
    raise NodeAttrError(name)
  def get_element(self, frame, anchor, sub, write=False):
    raise NodeTypeError('not subscriptable')
  def get_slice(self, frame, anchor, subs, write=False):
    raise NodeTypeError('not subscriptable')
  def get_iter(self, frame, anchor):
    raise NodeTypeError('not iterable')
  def get_reversed(self, frame, anchor):
    raise NodeTypeError('not reverse-iterable')
  def get_length(self, frame, anchor):
    raise NodeTypeError('no len()')
  def call(self, frame, anchor, args, kwargs):
    raise NodeTypeError('not callable')
  
  def get_name(self):
    raise NotImplementedError, self.__class__
  def desc1(self, _):
    raise NotImplementedError, self.__class__
  def describe(self):
    return self.desc1(set())
  def signature(self):
    return None
  def is_type(self, *_):
    return False


##  SimpleTypeNode
##
##  A SimpleTypeNode holds a particular type of value.
##  This type of nodes can be a leaf in a typeflow graph
##  and is not altered after creation.
##
class SimpleTypeNode(TypeNode):

  def __init__(self, typeobj):
    assert isinstance(typeobj, TypeNode), typeobj
    self.typeobj = typeobj
    TypeNode.__init__(self, [self])
    return

  def __repr__(self):
    return '<%s>' % self.typeobj.get_name()

  def desc1(self, _):
    return repr(self)
  

##  CompoundTypeNode
##
##  A CompoundTypeNode holds a multiple types of values that
##  can be potentially stored. This type of nodes can have
##  both inbound and outbound links and the data stored in the node
##  can be further propagated to other nodes.
##
class CompoundTypeNode(TypeNode):

  def __init__(self, nodes=None):
    TypeNode.__init__(self, [])
    if nodes:
      for obj in nodes:
        obj.connect(self.recv)
    return

  def __repr__(self):
    return '<CompoundTypeNode: %s>' % self.describe()

  def recv(self, src):
    for obj in src:
      self.update_type(obj)
    return
  
  def update_type(self, obj):
    if obj in self.types: return
    self.types.add(obj)
    for receiver in self.sendto:
      receiver(self)
    return True

  def desc1(self, done):
    if self in done:
      return '...'
    elif self.types:
      done.add(self)
      return '|'.join( sorted(set( obj.desc1(done) for obj in self )) )
    else:
      return '?'
                                  

##  UndefinedTypeNode
##
##  An UndefinedTypeNode is a special TypeNode object that
##  represents an undefined value. This node can be used as
##  a value in undefined variables or undefined attribues,
##  or a return value from illegal function calls. All the operation
##  on this node always returns itself (i.e. any operation on
##  undefined value is always undefined.)
##
class UndefinedTypeNode(TypeNode):
  
  def __init__(self, name=None):
    TypeNode.__init__(self, [])
    return
  
  def __repr__(self):
    return '(undef)'
  
  def desc1(self, _):
    return '(undef)'

  def recv(self, src):
    return
  def get_attr(self, frame, anchor, name, write=False):
    return self
  def get_element(self, frame, anchor, sub, write=False):
    return self
  def get_slice(self, frame, anchor, subs, write=False):
    return self
  def get_iter(self, frame, anchor):
    return self
  def get_reversed(self, frame, anchor):
    return self
  def get_length(self, frame, anchor):
    return self
  def call(self, frame, anchor, args, kwargs):
    return self


##  BuiltinObject
##
class BuiltinObject(SimpleTypeNode):

  def get_type(self):
    return self.typeobj
  
  def get_attr(self, frame, anchor, name, write=False):
    if name == '__class__':
      return self.get_type()
    return self.get_type().get_attr(frame, anchor, name, write=write)
  
  def is_type(self, *typeobjs):
    for typeobj in typeobjs:
      if self.typeobj is typeobj or issubclass(self.typeobj.__class__, typeobj.__class__): return True
    return False


##  BuiltinType
##
class BuiltinType(BuiltinObject):

  TYPE_NAME = None # must be defined by subclass
  TYPEOBJS = {}

  def __init__(self):
    self.initialize(self)
    SimpleTypeNode.__init__(self, self)
    return

  def __repr__(self):
    return '<type %s>' % self.get_name()
  
  @classmethod
  def get_type(klass):
    from basic_types import TypeType
    return TypeType.get_typeobj()
  
  @classmethod
  def is_type(klass, *typeobjs):
    from basic_types import TypeType
    return TypeType.get_typeobj() in typeobjs

  # get_name()
  # returns the name of the Python type of this object.
  @classmethod
  def get_name(klass):
    return klass.TYPE_NAME
  fullname = get_name

  # get_typeobj()
  @classmethod
  def get_typeobj(klass):
    if klass not in klass.TYPEOBJS:
      klass()
    return klass.TYPEOBJS[klass]

  @classmethod
  def initialize(klass, obj):
    klass.TYPEOBJS[klass] = obj
    return

  # default methods
  class InitMethod(BuiltinObject):
    def call(self, frame, anchor, args, kwargs):
      from basic_types import NoneType
      return NoneType.get_object()

  def get_attr(self, frame, anchor, name, write=False):
    raise NodeAttrError(name)


##  BuiltinCallable
##
##  A helper class to augment builtin objects (mostly type objects)
##  for behaving like a function.
##
class BuiltinCallable(object):

  def __init__(self, name, args=None, optargs=None, expts=None):
    args = (args or [])
    optargs = (optargs or [])
    self.name = name
    self.minargs = len(args)
    self.args = args+optargs
    self.expts = (expts or [])
    return
  
  def call(self, frame, anchor, args, kwargs):
    from config import ErrorConfig
    if len(args) < self.minargs:
      frame.raise_expt(ErrorConfig.InvalidNumOfArgs(self.minargs, len(args)))
      return UndefinedTypeNode()
    if len(self.args) < len(args):
      frame.raise_expt(ErrorConfig.InvalidNumOfArgs(len(self.args), len(args)))
      return UndefinedTypeNode()
    return self.process_args(frame, anchor, args, kwargs)

  def process_args(self, frame, anchor, args, kwargs):
    raise NotImplementedError, self.__class__


##  BuiltinConstCallable
##
class BuiltinConstCallable(BuiltinCallable):
  
  def __init__(self, name, retobj, args=None, optargs=None, expts=None):
    self.retobj = retobj
    BuiltinCallable.__init__(self, name, args=args, optargs=optargs, expts=expts)
    return

  def process_args(self, frame, anchor, args, kwargs):
    from config import ErrorConfig
    if kwargs:
      frame.raise_expt(ErrorConfig.NoKeywordArgs())
    for (i,arg1) in enumerate(args):
      assert isinstance(arg1, TypeNode)
      self.accept_arg(frame, anchor, i, arg1)
    for expt in self.expts:
      frame.raise_expt(expt)
    return self.retobj

  def accept_arg(self, frame, anchor, i, arg1):
    from exception import TypeChecker, SequenceTypeChecker
    s = 'arg %d' % i
    spec = self.args[i]
    if isinstance(spec, list):
      if spec == [TypeChecker.ANY]:
        checker = SequenceTypeChecker(frame, anchor, TypeChecker.ANY, s)
      else:
        checker = SequenceTypeChecker(frame, anchor, [ x.get_typeobj() for x in spec ], s)
    elif isinstance(spec, tuple):
      checker = TypeChecker(frame, [ x.get_typeobj() for x in spec ], s)
    elif spec == TypeChecker.ANY:
      checker = TypeChecker(frame, TypeChecker.ANY, s)
    else:
      checker = TypeChecker(frame, [spec.get_typeobj()], s)
    arg1.connect(checker.recv)
    return


##  BuiltinMethod
##
class BuiltinMethodType(BuiltinType):
  TYPE_NAME = 'builtin_method'


##  BuiltinMethod
##
class BuiltinMethod(BuiltinCallable, BuiltinObject):
  
  def __init__(self, name, args=None, optargs=None, expts=None):
    BuiltinObject.__init__(self, BuiltinMethodType.get_typeobj())
    BuiltinCallable.__init__(self, name, args=args, optargs=optargs, expts=expts)
    return

  def __repr__(self):
    return '<callable %s>' % self.name

##  BuiltinConstMethod
##
class BuiltinConstMethod(BuiltinConstCallable, BuiltinObject):

  def __init__(self, name, retobj, args=None, optargs=None, expts=None):
    BuiltinObject.__init__(self, BuiltinMethodType.get_typeobj())
    BuiltinConstCallable.__init__(self, name, retobj, args=args, optargs=optargs, expts=expts)
    return

  def __repr__(self):
    return '<callable %s>' % self.name
