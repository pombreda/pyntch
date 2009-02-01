#!/usr/bin/env python
import sys
stderr = sys.stderr


##  TreeReporter
##
class TreeReporter(object):

  def __init__(self, parent=None, name=None):
    self.children = []
    if parent:
      parent.register(name, self)
    return

  def register(self, name, child):
    self.children.append((name, child))
    return

  def show(self, p):
    return

  def showrec(self, out, i=0):
    h = '  '*i
    self.show(lambda s: out.write(h+s+'\n'))
    out.write('\n')
    for (name,reporter) in self.children:
      reporter.showrec(out, i+1)
    return
  
  
##  TypeNode
##
class NodeError(Exception): pass
class NodeTypeError(NodeError): pass
class NodeAttrError(NodeError): pass

class TypeNode(object):

  debug = 0
  N = 0

  def __init__(self, types):
    self.types = set(types)
    self.sendto = []
    TypeNode.N += 1
    if TypeNode.N % 1000 == 0:
      print >>stderr, 'nodes:', TypeNode.N
    return

  def __iter__(self):
    return iter(list(self.types))

  def connect(self, node, receiver=None):
    #assert isinstance(node, CompoundTypeNode), node
    if self.debug:
      print >>stderr, 'connect: %r -> %r' % (self, node)
    receiver = receiver or node.recv
    self.sendto.append(receiver)
    receiver(self)
    return

  def recv(self, src):
    raise NodeTypeError('cannot receive a value: %r' % self)

  def get_attr(self, name, write=False):
    raise NodeAttrError(name)
  def get_element(self, frame, subs, write=False):
    raise NodeTypeError('not subscriptable')
  def get_iter(self, frame):
    raise NodeTypeError('not iterator')
  def call(self, frame, args, kwargs):
    raise NodeTypeError('not callable')
  def get_seq(self, frame):
    from exception import ExceptionCatcher, StopIterationType
    frame1 = ExceptionCatcher(frame)
    frame1.add_handler(StopIterationType.occur(''))
    return self.get_iter(frame).get_attr('next').call(frame1, (), {})
  
  def create_sequence(self, elemall=None):
    raise NodeTypeError('not sequence type')
  def create_iter(self, elemall=None):
    raise NodeTypeError('not sequence type')
  
  def desc1(self, _):
    raise NotImplementedError, self
  def sig1(self, _):
    raise NotImplementedError, self
  def describe(self):
    return self.desc1(set())
  def signature(self):
    return self.sig1(set())


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

  def sig1(self, _):
    return self
  

##  CompoundTypeNode
##
class CompoundTypeNode(TypeNode):

  def __init__(self, nodes=None):
    self._sigs = set()
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
      s = []
      done = done.union([self])
      for obj in self.types:
        s.append(obj.desc1(done))
      return '|'.join(s)
    else:
      return '?'
                                  
  def recv(self, src):
    self.update_types(src.types)
    return

  W = 0
  T = 0
  
  def update_types(self, types):
    d = []
    for obj in types:
      if obj.signature() not in self._sigs: 
        d.append(obj)
    CompoundTypeNode.W += 1
    if CompoundTypeNode.W % 1000 == 0:
      print >>stderr, 'update:', CompoundTypeNode.W, CompoundTypeNode.T
    if not d: return
    CompoundTypeNode.T += len(d)
    self.types.update(d)
    self._sigs = set( obj.signature() for obj in self.types )
    for receiver in self.sendto:
      receiver(self)
    return


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
  def call(self, frame, args, kwargs):
    return self


##  BuiltinType
##
class BuiltinType(SimpleTypeNode):

  TYPE_NAME = None # must be defined by subclass
  TYPE_INSTANCE = None
  
  def __init__(self):
    self.__class__.TYPEOBJ = self
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
  TYPEOBJ = None
  @classmethod
  def get_typeobj(klass):
    if klass.TYPEOBJ == None:
      klass.TYPEOBJ = klass()
    return klass.TYPEOBJ


##  BuiltinObject
##
class BuiltinObject(SimpleTypeNode):

  def get_type(self):
    return self.typeobj

  def sig1(self, done):
    return self.get_type()
  
  def get_attr(self, name, write=False):
    return self.get_type().get_attr(name, write=write)
  
  def is_type(self, *typeobjs):
    for typeobj in typeobjs:
      if issubclass(self.typeobj.__class__, typeobj.__class__): return True
    return False
