#!/usr/bin/env python
##
##  typenode.py
##

import sys


##  TypeNode
##
class NodeError(Exception): pass
class NodeTypeError(NodeError): pass
class NodeAttrError(NodeError): pass

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
    if not klass.debug: return
    print >>sys.stderr, '%d nodes' % klass.N
    return

  def __init__(self, types):
    self.types = set(types)
    self.sendto = []
    TypeNode.inc()
    return

  def __iter__(self):
    return iter(list(self.types))

  def connect(self, receiver):
    if isinstance(receiver, CompoundTypeNode):
      receiver = receiver.recv
    if self.debug:
      print >>sys.stderr, 'connect: %r -> %r' % (self, receiver)
    if receiver in self.sendto: return False
    self.sendto.append(receiver)
    return receiver(self)

  def recv(self, src):
    raise NodeTypeError('cannot receive a value: %r' % self)

  def get_attr(self, name, write=False):
    raise NodeAttrError(name)
  def get_element(self, frame, subs, write=False):
    raise NodeTypeError('not subscriptable')
  def get_iter(self, frame):
    raise NodeTypeError('not iterator')
  def call(self, frame, args, kwargs, star, dstar):
    raise NodeTypeError('not callable')
  
  def get_name(self):
    raise NotImplementedError, self
  def desc1(self, _):
    raise NotImplementedError, self
  def describe(self):
    return self.desc1(set())
  def signature(self):
    return None


##  SimpleTypeNode
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
class CompoundTypeNode(TypeNode):

  def __init__(self, nodes=None):
    TypeNode.__init__(self, [])
    for obj in (nodes or []):
      obj.connect(self)
    return

  def __repr__(self):
    return '<CompoundTypeNode: %s>' % self.describe()

  def desc1(self, done):
    if self in done:
      return '...'
    elif self.types:
      done = done.union([self])
      return '|'.join( sorted(set( obj.desc1(done) for obj in self )) )
    else:
      return '?'
                                  
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


##  UndefinedTypeNode
##
class UndefinedTypeNode(TypeNode):
  
  def __init__(self, name=None):
    TypeNode.__init__(self, [])
    return
  
  def __repr__(self):
    return '(undef)'
  
  def desc1(self, _):
    return '(undef)'

  def get_attr(self, name, write=False):
    return self
  def get_element(self, frame, subs, write=False):
    return self
  def get_iter(self, frame):
    return self
  def call(self, frame, args, kwargs, star, dstar):
    return self


##  BuiltinObject
##
class BuiltinObject(SimpleTypeNode):

  def get_type(self):
    return self.typeobj
  
  def get_attr(self, name, write=False):
    return self.get_type().get_attr(name, write=write)
  
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
  def is_type(self, *typeobjs):
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
    def call(self, frame, args, kwargs, star, dstar):
      from basic_types import NoneType
      return NoneType.get_object()


##  BuiltinBasicType
##
class BuiltinBasicType(BuiltinType):

  TYPE_INSTANCE = None
  OBJECTS = {}

  # get_object()
  @classmethod
  def get_object(klass):
    assert klass.TYPE_INSTANCE
    if klass not in klass.OBJECTS:
      klass.OBJECTS[klass] = klass.TYPE_INSTANCE(klass.get_typeobj())
    return klass.OBJECTS[klass]
