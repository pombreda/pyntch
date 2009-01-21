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
    self.types = set(types)
    self.sendto = []
    return

  def connect(self, node, receiver=None):
    #assert isinstance(node, CompoundTypeNode), node
    if self.debug:
      print >>stderr, 'connect: %r :- %r' % (node, self)
    receiver = receiver or node.recv
    self.sendto.append(receiver)
    receiver(self)
    return

  def recv(self, src):
    raise NodeTypeError('cannot receive a value.')

  def get_attr(self, name):
    raise NodeAttrError(name)
  def get_element(self, caller, subs, write=False):
    raise NodeTypeError('not subscriptable')
  def get_iter(self, caller):
    raise NodeTypeError('not iterator')
  def call(self, caller, args):
    raise NodeTypeError('not callable')
  
  def describe(self):
    return self.desc1(set())
  def desc1(self, _):
    raise NotImplementedError


##  SimpleTypeNode
##
class SimpleTypeNode(TypeNode):

  def __init__(self, typeobj):
    assert isinstance(typeobj, TypeNode), typeobj
    self.typeobj = typeobj
    TypeNode.__init__(self, [self])
    return

  def __repr__(self):
    return '<%s>' % self.get_typename()

  def get_type(self):
    return self.typeobj

  def get_typename(self):
    return self.typeobj.get_name()

  def is_type(self, *typeobjs):
    for typeobj in typeobjs:
      if issubclass(self.typeobj.__class__, typeobj.__class__): return True
    return False

  def desc1(self, _):
    return repr(self)


##  CompoundTypeNode
##
class CompoundTypeNode(TypeNode):

  def __init__(self, types=None):
    self._hashval = 0
    TypeNode.__init__(self, types or [])
    return

  def __repr__(self):
    return self.describe()

  def __eq__(self, obj):
    return isinstance(obj, CompoundTypeNode) and self.types == obj.types
  def __hash__(self):
    return self._hashval

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
    diff = types.difference(self.types)
    if not diff: return
    self.types.update(diff)
    self._hashval = 0
    for obj in self.types:
      self._hashval ^= hash(obj)
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

  def get_attr(self, name):
    return self
  def get_element(self, caller, subs, write=False):
    return self
  def get_iter(self, caller):
    return self
  def call(self, caller, args):
    return self


##  BuiltinType
##
class BuiltinType(SimpleTypeNode):

  PYTHON_TYPE = 'undefined'
  
  def __init__(self):
    SimpleTypeNode.__init__(self, self)
    return

  def __repr__(self):
    return '<type %s>' % self.get_name()

  # get_name()
  # returns the name of the Python type of this object.
  @classmethod
  def get_name(klass):
    return klass.PYTHON_TYPE.__name__

  # get_type()
  TYPE = None
  @classmethod
  def get_type(klass):
    if not klass.TYPE:
      klass.TYPE = klass()
    return klass.TYPE

  # get_object()
  OBJECT = None
  @classmethod
  def get_object(klass):
    if not klass.OBJECT:
      klass.OBJECT = SimpleTypeNode(klass.get_type())
    return klass.OBJECT
