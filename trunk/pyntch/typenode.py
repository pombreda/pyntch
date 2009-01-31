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

  def __init__(self, types):
    self.types = types
    self.sendto = []
    return

  def __iter__(self):
    return iter(self.types)

  def connect(self, node, receiver=None):
    #assert isinstance(node, CompoundTypeNode), node
    if self.debug:
      print >>stderr, 'connect: %r -> %r' % (self, node)
    receiver = receiver or node.recv
    self.sendto.append(receiver)
    receiver(self)
    return

  def recv(self, src):
    raise NodeTypeError('cannot receive a value.')

  def get_attr(self, name, write=False):
    raise NodeAttrError(name)
  def get_element(self, frame, subs, write=False):
    raise NodeTypeError('not subscriptable')
  def get_iter(self, frame):
    raise NodeTypeError('not iterator')
  def call(self, frame, args, kwargs):
    raise NodeTypeError('not callable')
  def get_seq(self, frame):
    return self.get_iter(frame).get_attr('next').call(frame, (), {})
  
  def equal(self, obj, _=None):
    raise NotImplementedError
  def desc1(self, _):
    raise NotImplementedError
  def describe(self):
    return self.desc1(set())


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

  def equal(self, obj, _=None):
    return self is obj


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

  def equal(self, obj, done=None):
    if self is obj: return True
    if not isinstance(obj, CompoundTypeNode): return False
    if len(self.types) != len(obj.types): return False
    if done == None: done = set()
    if self in done or obj in done: return False
    done.add(self)
    done.add(obj)
    for (t1,t2) in zip(self.types, obj.types):
      if not t1.equal(t2, done): return False
    return True

  def desc1(self, done):
    if self in done:
      return '...'
    elif self.types:
      return ('|'.join( obj.desc1(done.union([self])) for obj in self.types ))
    else:
      return '?'
                                  
  def recv(self, src):
    self.update_types(src.types)
    return

  def update_types(self, types):
    d = []
    for obj1 in types:
      assert not isinstance(obj1, CompoundTypeNode), obj1
      for obj2 in self.types:
        assert not isinstance(obj2, CompoundTypeNode), obj2
        if obj1.equal(obj2): break
      else:
        d.append(obj1)
    if not d: return
    self.types.extend(d)
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
    SimpleTypeNode.__init__(self, self)
    return

  def __repr__(self):
    return '<type %s>' % self.get_name()

  @classmethod
  def get_type(klass):
    from builtin_types import TypeType
    return TypeType.get_typeobj()
  
  @classmethod
  def is_type(self, *typeobjs):
    from builtin_types import TypeType
    return TypeType.get_typeobj() in typeobjs

  # get_name()
  # returns the name of the Python type of this object.
  @classmethod
  def get_name(klass):
    return klass.TYPE_NAME

  # get_typeobj()
  TYPE = None
  @classmethod
  def get_typeobj(klass):
    if not klass.TYPE:
      klass.TYPE = klass()
    return klass.TYPE


##  BuiltinObject
##
class BuiltinObject(SimpleTypeNode):

  def get_type(self):
    return self.typeobj

  def get_attr(self, name, write=False):
    return self.get_type().get_attr(name, write=write)
  
  def is_type(self, *typeobjs):
    for typeobj in typeobjs:
      if issubclass(self.typeobj.__class__, typeobj.__class__): return True
    return False
