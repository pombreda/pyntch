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
    assert isinstance(typeobj, type) and issubclass(typeobj, TypeNode)
    self.typeobj = typeobj
    TypeNode.__init__(self, [self])
    return

  def __repr__(self):
    return '<%s>' % self.get_name()

  def get_name(self):
    return self.typeobj.get_name()

  def get_rank(self):
    return self.typeobj.get_rank()

  def is_type(self, *typeobjs):
    for typeobj in typeobjs:
      if issubclass(self.typeobj, typeobj): return True
    return False

  def desc1(self, _):
    return repr(self)


##  CompoundTypeNode
##
class CompoundTypeNode(TypeNode):

  def __init__(self, types=None):
    TypeNode.__init__(self, types or [])
    return

  def desc1(self, done):
    if self in done:
      return '...'
    else:
      return ('{%s}' % '|'.join( obj.desc1(done.union([self])) for obj in self.types ))
                                  
  def recv(self, src):
    self.update_types(src.types)
    return

  def update_types(self, types):
    if types.difference(self.types):
      self.types.update(types)
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
