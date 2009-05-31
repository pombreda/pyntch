#!/usr/bin/env python
import sys
from pyntch.typenode import TypeNode, CompoundTypeNode, NodeTypeError


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
    try:
      (module,lineno) = self.frame.getloc()
      return '%s at %s(%s)' % (self.expt, module.get_path(), lineno)
    except TypeError:
      return '%s at ???' % self.expt

  def desc1(self, _):
    return repr(self)


##  ExecutionFrame
##
##  An ExecutionFrame object is a place where an exception belongs.
##  Normally it's a body of function. Exceptions that are raised
##  within this frame are propagated to other ExecutionFrames which
##  invoke the function.
##
class ExecutionFrame(CompoundTypeNode):

  expt_debug = 0

  def __init__(self, parent, tree):
    self.parent = parent
    self.raised = set()
    if tree:
      self.loc = (tree._module, tree.lineno)
    else:
      self.loc = None
    CompoundTypeNode.__init__(self)
    if parent:
      assert isinstance(parent, ExecutionFrame), parent
      if self.expt_debug:
        print >>sys.stderr, 'connect_expt: %r <- %r' % (parent, self)
      self.connect(parent.recv)
    return

  def __repr__(self):
    loc = self.getloc()
    if loc:
      (module,lineno) = loc
      return '<Frame at %s(%s)>' % (module.get_path(), lineno)
    else:
      return '<Frame at ???>'

  def set_reraise(self):
    from pyntch.config import ErrorConfig
    self.raise_expt(ErrorConfig.RaiseOutsideTry())
    return

  def getloc(self):
    loc = None
    while self:
      loc = self.loc
      if loc: break
      self = self.parent
    return loc
  
  def raise_expt(self, expt):
    if not expt: return
    assert not isinstance(expt, CompoundTypeNode)
    if expt in self.raised: return
    self.raised.add(expt)
    if self.expt_debug:
      print >>sys.stderr, 'raise_expt: %r <- %r' % (self, expt)
    TracebackObject(expt, self).connect(self.recv)
    return

  def show(self, out):
    expts_here = []
    expts_there = []
    for expt in self:
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


##  ExceptionHandler
##
class ExceptionHandler(ExecutionFrame):

  def __init__(self, parent, expt):
    self.var = CompoundTypeNode()
    self.expt = expt
    self.reraise = False
    self.catchtypes = set()
    self.received = set()
    ExecutionFrame.__init__(self, parent, None)
    if expt:
      expt.connect(self.recv_expt)
    return

  def __repr__(self):
    return '<Handler for %r>' % ','.join(map(repr, self.catchtypes))

  def recv_expt(self, src):
    from pyntch.aggregate_types import TupleType
    for obj in src:
      if obj in self.received: continue
      self.received.add(obj)
      if obj.is_type(TupleType.get_typeobj()):
        self.recv_expt(obj.elemall)
      else:
        self.catchtypes.add(obj)
    return

  def set_reraise(self):
    self.reraise = True
    return

  def handle_expt(self, expt):
    if (not self.expt) or (expt.get_type() in self.catchtypes):
      expt.connect(self.var.recv)
      return not self.reraise
    return False


##  ExceptionCatcher
##
class ExceptionCatcher(ExecutionFrame):

  def __init__(self, parent):
    self.handlers = []
    self.received = set()
    ExecutionFrame.__init__(self, parent, None)
    return

  def __repr__(self):
    s = ', '.join(map(repr, self.handlers))
    x = self.getloc()
    if x:
      (module,lineno) = x
      return '<catch %s at %s(%s)>' % (s, module.get_path(), lineno)
    else:
      return '<Catch %s at ???>' % s
  
  def add_handler(self, src):
    handler = ExceptionHandler(self.parent, src)
    self.handlers.append(handler)
    return handler

  def recv(self, src):
    for obj in src:
      if obj in self.received: continue
      self.received.add(obj)
      assert isinstance(obj, TracebackObject), obj
      for frame in self.handlers:
        if frame.handle_expt(obj.expt): break
      else:
        self.update_type(obj)
    return


##  ExceptionMaker
##
##  Special behaviour on raising an exception.
##
class ExceptionMaker(CompoundTypeNode):
  
  def __init__(self, frame, anchor, exctype, excargs):
    self.frame = frame
    self.anchor = anchor
    self.exctype = exctype
    self.excargs = excargs
    self.processed = set()
    CompoundTypeNode.__init__(self)
    exctype.connect(self.recv_type)
    return
  
  def __repr__(self):
    return '<exception %s>' % (self.describe())

  def recv_type(self, src):
    from pyntch.klass import ClassType
    from pyntch.config import ErrorConfig
    for obj in src:
      if obj in self.processed: continue
      self.processed.add(obj)
      # Instantiate an object only if it is a class object.
      # Otherwise, just return the object given.
      if isinstance(obj, ClassType):
        try:
          result = obj.call(self.frame, self.anchor, self.excargs, {})
        except NodeTypeError:
          self.frame.raise_expt(ErrorConfig.NotCallable(obj))
          continue
        self.frame.raise_expt(result)
      else:
        self.frame.raise_expt(obj)
    return
