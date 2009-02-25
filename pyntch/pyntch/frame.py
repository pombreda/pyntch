#!/usr/bin/env python
import sys
from typenode import TypeNode, SimpleTypeNode, CompoundTypeNode, NodeTypeError
stderr = sys.stderr


##  TracebackObject
##
##  A TracebackObject is an exception object (or whatever is thrown)
##  associated with a specific execution frame.
##
class TracebackObject(TypeNode):

  def __init__(self, expt, frame):
    self.expt = expt
    self.frame = frame
    TypeNode.__init__(self, [self])
    return

  def __repr__(self):
    (module,lineno) = self.frame.getloc()
    return '%s at %s(%s)' % (self.expt, module.get_loc(), lineno)

  def desc1(self, _):
    return repr(self)


##  ExecutionFrame
##
##  An ExecutionFrame object is a place where an exception belongs.
##  Normally it's a body of function. Exceptions that are raised
##  within this frame are propagated to other ExecutionFrames which
##  invoke the function.
##
class ExecutionFrame(object):

  debug = 0

  def __init__(self, parent=None, tree=None):
    self.parent = parent
    self.loc = None
    self.done = set()
    self.buffer = CompoundTypeNode()
    if parent:
      self.connect_expt(parent)
    if tree:
      self.setloc(tree)
    return

  def __repr__(self):
    (module,lineno) = self.getloc()
    return '<Frame at %s(%s)>' % (module.get_loc(), lineno)

  def getloc(self):
    loc = None
    while not loc:
      loc = self.loc
      self = self.parent
    return loc

  def setloc(self, tree):
    self.loc = (tree._module, tree.lineno)
    return

  def connect_expt(self, frame):
    assert isinstance(frame, ExecutionFrame)
    if self.debug:
      print >>stderr, 'connect_expt: %r <- %r' % (frame, self)
    self.buffer.connect(frame.buffer)
    return
  
  def raise_expt(self, expt):
    assert not isinstance(expt, CompoundTypeNode)
    if expt in self.done: return
    self.done.add(expt)
    if self.debug:
      print >>stderr, 'raise_expt: %r <- %r' % (self, expt)
    TracebackObject(expt, self).connect(self.buffer)
    return

  def associate_frame(self, frame):
    return

  def show(self, out):
    expts_here = []
    expts_there = []
    for expt in self.buffer:
      frame = expt.frame
      while frame:
        if frame == self:
          expts_here.append(expt)
          break
        frame = frame.parent
      else:
        expts_there.append(expt)
    for expt in sorted(expts_here, key=lambda expt:expt.frame.getloc()):
      out.write('  raises %r' % expt)
    for expt in sorted(expts_there, key=lambda expt:expt.frame.getloc()):
      out.write('  [raises %r]' % expt)
    return


##  ExceptionCatcher
##
class ExceptionCatcher(ExecutionFrame):

  class ExceptionFilter(CompoundTypeNode):
    
    def __init__(self, catcher):
      self.catcher = catcher
      self.handlers = []
      self.done = set()
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      if self.catcher.catchall: return
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        assert isinstance(obj, TracebackObject), obj
        assert isinstance(obj.expt, SimpleTypeNode), obj.expt
        for (typeobj, var) in self.handlers:
          if obj.expt.is_type(typeobj):
            obj.expt.connect(var)
            break
        else:
          self.update_type(obj)
      return

    def recv_expt(self, src, var):
      for obj in src:
        self.handlers.append((obj, var))
      return

    def catch(self, obj, var):
      obj.connect(lambda src: self.recv_expt(src, var))
      return

  def __init__(self, parent):
    self.parent = parent
    self.catchall = False
    self.vars = {}
    self.done = set()
    self.buffer = self.ExceptionFilter(self)
    if parent:
      self.connect_expt(parent)
    return
  
  def __repr__(self):
    if self.catchall:
      return '<catch all>'
    else:
      return '<catch %s>' % ', '.join(map(repr, self.vars.iterkeys()))

  def add_all(self):
    self.catchall = True
    return
  
  def add_handler(self, src):
    var = CompoundTypeNode()
    src.connect(lambda src: self.recv_handler_expt(src, var))
    return var

  def recv_handler_expt(self, src, var):
    from aggregate_types import TupleType
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      if obj.is_type(TupleType.get_typeobj()):
        self.buffer.catch(obj.elemall, var)
      else:
        self.buffer.catch(obj, var)
    return


##  ExceptionMaker
##
##  Special behaviour on raising an exception.
##
class ExceptionMaker(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent, exctype, excargs):
    self.exctype = exctype
    self.excargs = excargs
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent=parent)
    exctype.connect(self.recv_type)
    return
  
  def __repr__(self):
    return '<exception %s>' % (self.describe())

  def recv_type(self, src):
    from klass import ClassType
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      # Instantiate an object only if it is a class object.
      # Otherwise, just return the object given.
      if isinstance(obj, ClassType):
        try:
          result = obj.call(self, self.excargs, {})
        except NodeTypeError:
          self.raise_expt(TypeErrorType.occur('cannot call: %r might be %r' % (self.exctype, obj)))
          continue
        self.raise_expt(result)
      else:
        self.raise_expt(obj)
    return


##  MustBeDefinedNode
##
class MustBeDefinedNode(CompoundTypeNode, ExecutionFrame):

  nodes = None
  
  def __init__(self, parent=None):
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent=parent)
    MustBeDefinedNode.nodes.append(self)
    return

  def check_undefined(self):
    return
  
  @classmethod
  def reset(klass):
    klass.nodes = []
    return
  
  @classmethod
  def check(klass):
    for node in klass.nodes:
      node.check_undefined()
    return
