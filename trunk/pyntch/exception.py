#!/usr/bin/env python
import sys
stderr = sys.stderr

from compiler import ast
from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError


##  ExceptionFrame
##
##  An ExceptionFrame object is a place where an exception belongs.
##  Normally it's a body of function. Exceptions that are raised
##  within this frame are propagated to other ExceptionFrames which
##  invoke the function.
##
class ExceptionFrame(object):

  debug = 0

  def __init__(self):
    self.expts = set()
    self.callers = []
    return

  def connect_expt(self, frame):
    assert isinstance(frame, ExceptionFrame)
    self.callers.append(frame)
    if self.debug:
      print >>stderr, 'connect_expt: %r :- %r' % (frame, self)
    self.propagate_expts(self.expts)
    return
  
  def add_expt(self, loc, expt):
    expt.loc = loc
    if self.debug:
      print >>stderr, 'add_expt: %r <- %r' % (self, expt)
    expt.connect(self, self.recv_expt)
    return

  def recv_expt(self, expt):
    if expt in self.expts: return
    self.expts.update(expt.types)
    self.propagate_expts(self.expts)
    return
  
  def propagate_expts(self, expts):
    for frame in self.callers:
      frame.update_expts(expts)
    return

  def update_expts(self, expts):
    if expts.difference(self.expts):
      self.expts.update(expts)
      self.propagate_expts(self.expts)
    return

  def show(self, p):
    for expt in self.expts:
      p('  raises %r' % expt)
    return


##  ExceptionCatcher
##
class ExceptionCatcher(ExceptionFrame):
  
  def __init__(self, parent):
    ExceptionFrame.__init__(self)
    self.handlers = {}
    self.catchall = False
    ExceptionFrame.connect_expt(self, parent)
    return
  
  def __repr__(self):
    if self.catchall:
      return '<except all>'
    else:
      return '<except %s>' % ', '.join(map(repr, self.handlers.iterkeys()))

  def add_all(self):
    self.catchall = True
    return
  
  def add_handler(self, expt):
    if expt not in self.handlers:
      self.handlers[expt] = (CompoundTypeNode(), CompoundTypeNode())
    expt.connect(self, self.recv_handler_expt)
    (_,var) = self.handlers[expt]
    return var

  def recv_handler_expt(self, src):
    from builtin_types import TupleType
    (t,_) = self.handlers[src]
    for expt in src.types:
      if isinstance(expt, TupleType):
        expt.elemall.connect(t)
      else:
        expt.connect(t)
    return

  def propagate_expts(self, expts):
    if self.catchall: return
    remainder = set()
    for expt in expts:
      for (t,var) in self.handlers.itervalues():
        if t == expt: # XXX support hierarchical type
          expt.connect(var)
          break
      else:
        remainder.add(expt)
    ExceptionFrame.propagate_expts(self, remainder)
    return


##  ExceptionRaiser
##
class ExceptionRaiser(ExceptionFrame):

  nodes = None

  def __init__(self, parent, loc=None):
    ExceptionFrame.__init__(self)
    assert not loc or isinstance(loc, ast.Node), loc
    self.loc = loc
    ExceptionFrame.connect_expt(self, parent)
    ExceptionRaiser.nodes.append(self)
    return
  
  def raise_expt(self, expt):
    ExceptionFrame.add_expt(self, self.loc, expt)
    return
  
  def finish(self):
    return
  
  ###
  @classmethod
  def reset(klass):
    klass.nodes = []
    return
  
  @classmethod
  def runall(klass):
    for node in klass.nodes:
      node.finish()
    return


##  ExceptionType
##
class ExceptionType(SimpleTypeNode):

  def __init__(self, name, msg, loc=None):
    SimpleTypeNode.__init__(self, self.__class__)
    assert not loc or isinstance(loc, ast.Node), loc
    self.loc = loc
    self.name = name
    self.msg = msg
    return

  def __repr__(self):
    if self.loc:
      return '<%s: %s> at %s(%d)' % (self.name, self.msg, self.loc._modname, self.loc.lineno)
    else:
      return '<%s: %s>' % (self.name, self.msg)


##  ExceptinoMaker
##
##  Special behaviour on raising an exception.
##
class ExceptionMaker(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, exctype, excargs):
    CompoundTypeNode.__init__(self)
    self.exctype = exctype
    self.excargs = excargs
    ExceptionRaiser.__init__(self, parent_frame, loc)
    exctype.connect(self, self.recv_type)
    return
  
  def __repr__(self):
    return '<exception %r(%s)>' % (self.exctype, ','.join(map(repr, self.excargs)))

  def recv_type(self, src):
    from function import ClassType
    for obj in src.types:
      # Instantiate an object only if it is a class object.
      # Otherwise, just return the object given.
      if isinstance(obj, ClassType):
        try:
          result = obj.call(self, self.excargs)
        except NodeTypeError:
          self.raise_expt(ExceptionType(
            'TypeError',
            'cannot call: %r might be %r' % (self.exctype, obj)))
          continue
        for parent in self.callers:
          result.connect_expt(parent)
        result.connect(self)
      else:
        obj.connect(self)
    return


##  TypeChecker
##
class TypeChecker(CompoundTypeNode):
  
  def __init__(self, parent_frame, types, blame=None):
    CompoundTypeNode.__init__(self)
    self.parent_frame = parent_frame
    self.types = types
    self.validtypes = set()
    self.blame = blame
    for obj in types:
      obj.connect(self, self.recv_type)
    return

  def __repr__(self):
    return ('<TypeChecker: %s: {%s}>' % 
            (','.join(map(repr, self.types)),
             '|'.join(map(repr, self.validtypes))))

  def recv_type(self, src):
    self.validtypes.update(src.types)
    return
  
  def recv(self, src):
    types = set()
    for obj in src.types:
      if isinstance(obj, tuple(self.validtypes)):
        types.add(obj)
      elif self.blame:
        self.parent_frame.raise_expt(ExceptionType(
          'TypeError',
          '%s (%s) must be {%s}' % (self.blame, obj, '|'.join(map(repr, self.validtypes)))))
    self.update_types(types)
    return


##  ElementTypeChecker
##
class ElementTypeChecker(TypeChecker):
  
  def recv(self, src):
    for obj in src.types:
      try:
        obj.get_iter(self.parent_frame).connect(self, self.recv_elemobj)
      except NodeTypeError:
        if self.blame:
          self.parent_frame.raise_expt(ExceptionType(
            'TypeError',
            '%s (%s) must be iterable' % (self.blame, obj)))
    return
  
  def recv_elemobj(self, src):
    types = set()
    for obj in src.types:
      if obj in self.validtypes:
        types.add(obj)
      elif self.blame:
        self.parent_frame.raise_expt(ExceptionType(
          'TypeError',
          '%s (%s) must be [{%s}]' % (self.blame, obj, '|'.join(map(repr, self.validtypes)))))
    self.update_types(types)
    return
