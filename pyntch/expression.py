#!/usr/bin/env python

from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError
from frame import ExceptionType, ExceptionRaiser
#from builtin_types import NumberType, BoolType, ListType, BaseStringType, BUILTIN_TYPE


##  FunCall
##
class FunCall(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, func, args):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.func = func
    self.args = args
    func.connect(self, self.recv_func)
    return

  def __repr__(self):
    return '<%r(%s)>' % (self.func, ','.join(map(repr, self.args)))

  def recv_func(self, src):
    for func in src.types:
      try:
        result = func.call(self, self.args)
        result.connect_expt(self)
        result.connect(self)
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'TypeError',
          'cannot call: %r might be %r' % (self.func, func)))
    return


##  AttrRef
##
class AttrRef(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, attrname):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target = target
    self.attrname = attrname
    self.objs = set()
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return '%r.%s' % (self.target, self.attrname)

  def recv_target(self, src):
    self.objs.update(src.types)
    for obj in self.objs:
      try:
        attr = obj.get_attr(self.attrname)
        attr.connect(self)
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'AttributeError',
          'cannot get attribute: %r might be %r, no attr %s' % (self.target, obj, self.attrname)))
    return

  def finish(self):
    if not self.types:
      self.raise_expt(ExceptionType(
        'AttributeError',
        'attribute not defined: %r.%s' % (self.target, self.attrname)))
    return


##  AttrAssign
##
class AttrAssign(CompoundTypeNode):
  
  def __init__(self, tree, target, attrname, value):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.target = target
    self.objs = set()
    self.attrname = attrname
    self.value = value
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r.%s, %r)' % (self.target, self.attrname, self.value)

  def recv_target(self, src):
    self.objs.update(src.types)
    for obj in self.objs:
      attr = obj.get_attr(self.attrname)
      self.value.connect(attr)
    return


##  BinaryOp
##
class BinaryOp(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, op, left, right):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.op = op
    self.left_types = set()
    self.right_types = set()
    self.combinations = set()
    left.connect(self, self.recv_left)
    right.connect(self, self.recv_right)
    return
  
  def __repr__(self):
    return '%s(%r,%r)' % (self.op, self.left_types, self.right_types)

  def recv_left(self, src):
    self.left_types.update(src.types)
    self.update()
    return
  def recv_right(self, src):
    self.right_types.update(src.types)
    self.update()
    return

  VALID_TYPES = {
    ('str', 'Mul', 'int'): 'str',
    ('unicode', 'Mul', 'int'): 'unicode',
    }
  def update(self):
    from builtin_types import NumberType, BaseStringType, BUILTIN_TYPE
    for lobj in self.left_types:
      for robj in self.right_types:
        if (lobj,robj) in self.combinations: continue
        self.combinations.add((lobj,robj))
        if (isinstance(lobj, NumberType) and
            isinstance(robj, NumberType)):
          if self.op in ('Add','Sub','Mul','Div','Mod','FloorDiv'):
            if lobj.rank < robj.rank:
              self.update_types(set([robj]))
            else:
              self.update_types(set([lobj]))
            continue
        if (isinstance(lobj, BaseStringType) and
            isinstance(robj, BaseStringType) and
            self.op == 'Add'):
          self.update_types(set([robj]))
          continue
        k = (lobj.NAME, self.op, robj.NAME)
        if k in self.VALID_TYPES:
          v = BUILTIN_TYPE[self.VALID_TYPES[k]]
          self.update_types(set([v]))
          continue
        self.raise_expt(ExceptionType(
          'TypeError',
          'unsupported operand %s for %r and %r' % (self.op, lobj, robj)))
    return

class AssignOp(BinaryOp): pass


##  CompareOp
##
class CompareOp(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, expr0, comps):
    from builtin_types import BoolType
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.types.add(BoolType.get())
    self.expr0 = expr0
    self.comps = comps
    self.expr0.connect(self)
    for (_,expr) in self.comps:
      expr.connect(self)
    return
  
  def __repr__(self):
    return 'cmp(%r %s)' % (self.expr0,
                           ','.join( '%s %r' % (op,expr) for (op,expr) in self.comps ))
  
  def recv(self, _):
    # ignore because CompareOp always returns bool.
    return


##  BooleanOp
##
class BooleanOp(CompoundTypeNode):
  
  def __init__(self, op, nodes):
    from builtin_types import BoolType
    CompoundTypeNode.__init__(self)
    self.types.add(BoolType.get())
    self.op = op
    self.nodes = nodes
    for node in self.nodes:
      node.connect(self)
    return
  
  def __repr__(self):
    return '%s(%s)' % (self.op, ','.join(map(repr, self.nodes)))


##  SubRef
##
class SubRef(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, subs):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target = target
    self.objs = set()
    self.subs = subs
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return '%r[%s]' % (self.target, ':'.join(map(repr, self.subs)))

  def recv_target(self, src):
    self.objs.update(src.types)
    for obj in self.objs:
      try:
        obj.get_element(self.subs).connect(self)
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'TypeError',
          'unsubscriptable object: %r' % obj))
    return


##  SubAssign
##
class SubAssign(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, subs, value):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target = target
    self.objs = set()
    self.subs = subs
    self.value = value
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r%r, %r)' % (self.target, self.subs, self.value)

  def recv_target(self, src):
    self.objs.update(src.types)
    for obj in self.objs:
      try:
        self.value.connect(obj.get_element(self.subs, write=True))
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'TypeError',
          'unsubscriptable object: %r' % obj))
    return


##  GeneratorSlot
##
class GeneratorSlot(CompoundTypeNode):

  def __init__(self, value):
    CompoundTypeNode.__init__(self)
    self.types.add(self)
    self.value = value
    return


##  IterRef
##
class IterRef(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target = target
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'iter(%r)' % (self.target,)

  def recv_target(self, src):
    for obj in src.types:
      try:
        obj.get_iter().connect(self)
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'TypeError',
          '%r might not be an iterator: %r' % (self.target, obj)))
        continue
    return

    
