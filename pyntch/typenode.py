#!/usr/bin/env python
import sys
stderr = sys.stderr


##  TypeNode
##
class NodeError(Exception): pass
class NodeTypeError(NodeError): pass
class InvalidMethodError(NodeError): pass

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
    self.sendto.append((node, receiver))
    (receiver or node.recv)(self)
    return

  def recv(self, src):
    raise TypeError('TypeNode cannot receive a value.')

  def call(self, caller, args):
    raise NodeTypeError('not callable')
  def get_attr(self, name):
    raise NodeTypeError('no attribute')
  def get_element(self, subs, write=False):
    raise NodeTypeError('not subscriptable')
  def get_iter(self):
    raise NodeTypeError('not iterator')
  
  def describe(self):
    return self.desc1(set())
  def desc1(self, _):
    raise NotImplementedError


##  SimpleTypeNode
##
class SimpleTypeNode(TypeNode):

  NAME = None

  def __init__(self):
    TypeNode.__init__(self, [self])
    return

  def __repr__(self):
    raise NotImplementedError, self.__class__

  def desc1(self, _):
    return repr(self)


##  CompoundTypeNode
##
class CompoundTypeNode(TypeNode):

  def __init__(self):
    TypeNode.__init__(self, [])
    return

  def desc1(self, done):
    if self in done:
      return '...'
    else:
      done.add(self)
      return ('{%s}' % '|'.join( obj.desc1(done) for obj in self.types ))
                                  
  def recv(self, src):
    self.update_types(src.types)
    return

  def update_types(self, types):
    if types.difference(self.types):
      self.types.update(types)
      for (node,receiver) in self.sendto:
        (receiver or node.recv)(self)
    return


##  UndefinedTypeNode
##
class UndefinedTypeNode(TypeNode):
  
  def __init__(self, name):
    TypeNode.__init__(self, [])
    return
  
  def __repr__(self):
    return '(undef)'
  
  def desc1(self, _):
    return '(undef)'