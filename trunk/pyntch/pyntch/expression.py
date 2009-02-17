#!/usr/bin/env python

from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError
from frame import ExecutionFrame, MustBeDefinedNode
from exception import TypeErrorType, AttributeErrorType, ValueErrorType


##  FunCall
##
class FunCall(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, func, args, kwargs={}):
    self.func = func
    self.args = args
    self.kwargs = kwargs
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    func.connect(self, self.recv_func)
    return

  def __repr__(self):
    return ('<call %r(%s)>' %
            (self.func, ', '.join(map(repr, self.args) +
                                  [ '%s=%r' % (k,v) for (k,v) in self.kwargs.iteritems() ])))

  def recv_func(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        obj.call(self, self.args, self.kwargs).connect(self)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('cannot call: %r might be %r' % (self.func, obj)))
    return


##  AttrRef
##
class AttrRef(MustBeDefinedNode):
  
  def __init__(self, parent_frame, loc, target, attrname):
    self.target = target
    self.attrname = attrname
    self.done = set()
    MustBeDefinedNode.__init__(self, parent_frame, loc)
    target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return '%r.%s' % (self.target, self.attrname)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        obj.get_attr(self.attrname).connect(self)
      except NodeAttrError:
        self.raise_expt(AttributeErrorType.maybe(
          'cannot get attribute: %r might be %r, no attr %s.' % (self.target, obj, self.attrname)))
    return

  def check_undefined(self):
    if not self.types:
      self.raise_expt(AttributeErrorType.occur('attribute not defined: %r.%s' % (self.target, self.attrname)))
    return


##  AttrAssign
##
class AttrAssign(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, target, attrname, value):
    self.target = target
    self.attrname = attrname
    self.value = value
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r.%s, %r)' % (self.target, self.attrname, self.value)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        self.value.connect(obj.get_attr(self.attrname, write=True))
      except (NodeAttrError, NodeTypeError):
        self.raise_expt(AttributeErrorType.occur(
          'cannot assign attribute: %r might be %r, no attr %s' % (self.target, obj, self.attrname)))
    return


##  BinaryOp
##
class BinaryOp(MustBeDefinedNode):
  
  def __init__(self, parent_frame, loc, op, left, right):
    assert op in ('Add','Sub','Mul','Div','Mod','FloorDiv','Power',
                  'Bitand','Bitor','Bitxor','RightShift','LeftShift')
    self.op = op
    self.left = left
    self.right = right
    self.done = set()
    self.tupleobj = self.listobj = None
    MustBeDefinedNode.__init__(self, parent_frame, loc)
    left.connect(self, self.recv_left)
    right.connect(self, self.recv_right)
    return
  
  def __repr__(self):
    return '%s(%r,%r)' % (self.op, self.left, self.right)

  def recv_left(self, left):
    for lobj in left:
      for robj in self.right:
        self.update_op(lobj, robj)
    return
  
  def recv_right(self, right):
    for lobj in self.left:
      for robj in right:
        self.update_op(lobj, robj)
    return

  LMETHOD = {
    'Add': '__add__',
    'Sub': '__sub__',
    'Mul': '__mul__',
    'Div': '__div__',
    'Mod': '__mod__',
    'FloorDiv': '__floordiv__',
    'Power': '__pow__',
    'Bitand': '__and__',
    'Bitor': '__or__',
    'Bitxor': '__xor__',
    'RightShift': '__rshift__',
    'LeftShift': '__lshift__',
    }

  RMETHOD = {
    'Add': '__radd__',
    'Sub': '__rsub__',
    'Mul': '__rmul__',
    'Div': '__rdiv__',
    'Mod': '__rmod__',
    'FloorDiv': '__rfloordiv__',
    'Power': '__rpow__',
    'Bitand': '__rand__',
    'Bitor': '__ror__',
    'Bitxor': '__rxor__',
    'RightShift': '__rrshift__',
    'LeftShift': '__rlshift__',
    }
  
  VALID_TYPES = {
    ('str', 'Mul', 'int'): 'str',
    ('int', 'Mul', 'str'): 'str',
    ('unicode', 'Mul', 'int'): 'unicode',
    ('int', 'Mul', 'unicode'): 'unicode',
    }

  def update_op(self, lobj, robj):
    from basic_types import NumberType, IntType, BaseStringType, BUILTIN_OBJECT
    from aggregate_types import ListType, ListObject, TupleType
    from klass import InstanceObject
    if (lobj,robj) in self.done: return
    self.done.add((lobj,robj))
    # special handling for a formatting (%) operator
    ltype = lobj.get_type()
    rtype = robj.get_type()
    if (lobj.is_type(BaseStringType.get_typeobj()) and
        self.op == 'Mod'):
      lobj.connect(self)
      return
    # for numeric operation, the one with a higher rank is chosen.
    if (lobj.is_type(NumberType.get_typeobj()) and robj.is_type(NumberType.get_typeobj()) and
        self.op in ('Add','Sub','Mul','Div','Mod','FloorDiv','Power','LeftShift','RightShift')):
      if ltype.get_rank() < rtype.get_rank():
        robj.connect(self)
      else:
        lobj.connect(self)
      return
    if (lobj.is_type(IntType.get_typeobj()) and robj.is_type(IntType.get_typeobj()) and
        self.op in ('Bitand','Bitor','Bitxor')):
      robj.connect(self)
      return
    # for string operation, only Add is supported.
    if (lobj.is_type(BaseStringType.get_typeobj()) and robj.is_type(BaseStringType.get_typeobj()) and
        self.op == 'Add'):
      robj.connect(self)
      return
    # for list operation, only Add and Mul is supported.
    if (self.op == 'Add' and
        (lobj.is_type(ListType.get_typeobj()) and robj.is_type(ListType.get_typeobj()))):
      if not self.listobj:
        self.listobj = ListType.create_list()
        self.listobj.connect(self)
      lobj.connect_element(self.listobj)
      robj.connect_element(self.listobj)
      return
    if self.op == 'Mul':
      if lobj.is_type(ListType.get_typeobj()) and robj.is_type(IntType.get_typeobj()):
        lobj.connect(self)
        return
      elif lobj.is_type(IntType.get_typeobj()) and robj.is_type(ListType.get_typeobj()):
        robj.connect(self)
        return
    # for tuple operation, only Add and Mul is supported.
    if (self.op == 'Add' and
        (lobj.is_type(TupleType.get_typeobj()) and robj.is_type(TupleType.get_typeobj()))):
      if not self.tupleobj:
        self.tupleobj = TupleType.create_tuple()
        self.tupleobj.connect(self)
      lobj.connect_element(self.tupleobj)
      robj.connect_element(self.tupleobj)
      return
    if self.op == 'Mul':
      if lobj.is_type(TupleType.get_typeobj()) and robj.is_type(IntType.get_typeobj()):
        lobj.connect(self)
        return
      elif lobj.is_type(IntType.get_typeobj()) and robj.is_type(TupleType.get_typeobj()):
        robj.connect(self)
        return
    # other operations.
    k = (ltype.get_name(), self.op, rtype.get_name())
    if k in self.VALID_TYPES:
      BUILTIN_OBJECT[self.VALID_TYPES[k]].connect(self)
      return
    # Handle optional methods.
    if isinstance(lobj, InstanceObject):
      try:
        lobj.get_attr(self.LMETHOD[self.op]).optcall(self, [robj], {}).connect(self)
      except (NodeAttrError, NodeTypeError):
        pass
    if isinstance(robj, InstanceObject):
      try:
        robj.get_attr(self.RMETHOD[self.op]).optcall(self, [lobj], {}).connect(self)
      except (NodeAttrError, NodeTypeError):
        pass
    return
  
  def check_undefined(self):
    if not self.types:
      self.raise_expt(TypeErrorType.occur('unsupported operand %s for %s and %s' %
                                          (self.op, self.left.describe(), self.right.describe())))
    return


##  AssignOp
##
class AssignOp(BinaryOp):

  OPS = {
    '+=': 'Add',
    '-=': 'Sub',
    '*=': 'Mul',
    '/=': 'Div',
    '%=': 'Mod',
    '//=': 'FloorDiv',
    '**=': 'Power',
    '&=': 'Bitand',
    '|=': 'Bitor',
    '^=': 'Bitxor',
    '>>=': 'RightShift',
    '<<=': 'LeftShift',
    }
  
  def __init__(self, parent_frame, loc, op, left, right):
    BinaryOp.__init__(self, parent_frame, loc, self.OPS[op], left, right)
    self.connect(left)
    return


##  UnaryOp
##
class UnaryOp(MustBeDefinedNode):

  METHOD = {
    'UnaryAdd': '__pos__',
    'UnarySub': '__neg__',
    'Invert': '__invert__',
    }
  
  def __init__(self, parent_frame, loc, op, value):
    self.value = value
    self.op = op
    self.done = set()
    MustBeDefinedNode.__init__(self, parent_frame, loc)
    value.connect(self, self.recv_value)
    return
  
  def __repr__(self):
    return '%s(%r)' % (self.op, self.value)
  
  def recv_value(self, src):
    from basic_types import NumberType
    from klass import InstanceObject
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      if obj.is_type(NumberType.get_typeobj()):
        obj.connect(self)
      elif isinstance(obj, InstanceObject):
        try:
          obj.get_attr(self.METHOD[self.op]).optcall(self, [], {}).connect(self)
        except (NodeAttrError, NodeTypeError):
          pass
    return


##  CompareOp
##
class CompareOp(CompoundTypeNode, ExecutionFrame):

  LMETHOD = {
    '==': '__eq__',
    '!=': '__ne__',
    '<=': '__le__',
    '>=': '__ge__',
    '<': '__lt__',
    '>': '__gt__',
    'in': '__contains__',
    'not in': '__contains__',
    }
  
  def __init__(self, parent_frame, loc, op, left, right):
    from basic_types import BoolType
    self.op = op
    self.left = left
    self.right = right
    self.done = set()
    CompoundTypeNode.__init__(self, [BoolType.get_object()])
    ExecutionFrame.__init__(self, parent_frame, loc)
    left.connect(self, self.recv_left)
    return
  
  def __repr__(self):
    return '%s(%r,%r)' % (self.op, self.left, self.right)

  def recv_left(self, left):
    from klass import InstanceObject
    for lobj in left:
      if lobj in self.done: continue
      self.done.add(lobj)
      if isinstance(lobj, InstanceObject):
        try:
          lobj.get_attr(self.LMETHOD[self.op]).optcall(self, [self.right], {})
        except (KeyError, NodeAttrError, NodeTypeError):
          pass
    return


##  BooleanOp
##
class BooleanOp(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, op, nodes):
    from basic_types import BoolType
    self.op = op
    self.nodes = nodes
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    if op == 'Or' and not [ 1 for node in nodes if isinstance(node, SimpleTypeNode) ]:
      BoolType.get_object().connect(self)
    for node in self.nodes:
      node.connect(self)
    return
  
  def __repr__(self):
    return '%s(%s)' % (self.op, ','.join(map(repr, self.nodes)))


##  NotOp
##
class NotOp(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, value):
    from basic_types import BoolType
    self.value = value
    CompoundTypeNode.__init__(self, [BoolType.get_object()])
    ExecutionFrame.__init__(self, parent_frame, loc)
    self.value.connect(self)
    return
  
  def __repr__(self):
    return 'not %r' % (self.value)
  
  def recv(self, _):
    # ignore because NotOp always returns bool.
    return


##  IfExpOp
##
class IfExpOp(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, test, then, else_):
    self.test = test
    self.then = then
    self.else_ = else_
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    then.connect(self)
    else_.connect(self)
    return
  
  def __repr__(self):
    return '%r if %r else %r' % (self.then, self.test, self.else_)


##  SubRef
##
class SubRef(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, target, subs):
    self.target = target
    self.subs = subs
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return '%r[%s]' % (self.target, ':'.join(map(repr, self.subs)))

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        obj.get_element(self, self.subs).connect(self)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


##  SubAssign
##
class SubAssign(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, target, subs, value):
    self.target = target
    self.subs = subs
    self.value = value
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r%r, %r)' % (self.target, self.subs, self.value)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        self.value.connect(obj.get_element(self, self.subs, write=True))
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


##  IterRef
##
class IterRef(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, target):
    self.target = target
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'iter(%r)' % (self.target,)

  def recv_target(self, src):
    from aggregate_types import ElementGetter
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      ElementGetter(obj, self).connect(self)
    return


##  SliceRef
##
class SliceRef(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, target, lower, upper, step=None):
    self.target = target
    self.lower = lower
    self.upper = upper
    self.step = step
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    if self.lower and self.upper:
      return '%r[%r:%r]' % (self.target, self.lower, self.upper)
    elif self.lower:
      return '%r[%r:]' % (self.target, self.lower)
    elif self.upper:
      return '%r[:%r]' % (self.target, self.upper)
    else:
      return '%r[:]' % self.target

  def recv_target(self, src):
    from aggregate_types import TupleType, ListType, TupleObject
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        obj.get_element(self, [self.lower, self.upper])
        # if an element can be retrieved from the object,
        # it can be the result of the slice of itself.
        obj.connect(self)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


##  SliceAssign
##
class SliceAssign(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, target, lower, upper, value):
    from aggregate_types import ElementGetter
    self.target = target
    self.lower = lower
    self.upper = upper
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    self.elemall = ElementGetter(value, self)
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r[%r:%r], %r)' % (self.target, self.lower, self.upper, self.value)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        self.elemall.connect(obj.get_element(self, [self.lower, self.upper], write=True))
      except (NodeTypeError, NodeAttrError):
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


class SliceObject(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent_frame, loc, nodes):
    self.nodes = nodes
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    return


##  TupleUnpack
##
class TupleUnpack(CompoundTypeNode, ExecutionFrame):

  ##  Element
  ##
  class Element(CompoundTypeNode):
    
    def __init__(self, tup, i):
      self.tup = tup
      self.i = i
      CompoundTypeNode.__init__(self)
      return

    def __repr__(self):
      return '<TupleElement: %r[%d]>' % (self.tup, self.i)
  
  #
  def __init__(self, parent_frame, loc, tupobj, nelements):
    self.tupobj = tupobj
    self.elements = [ self.Element(self, i) for i in xrange(nelements) ]
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent_frame, loc)
    self.tupobj.connect(self, self.recv_tupobj)
    return

  def __repr__(self):
    return '<TupleUnpack: %r>' % (self.tupobj,)

  def get_nth(self, i):
    return self.elements[i]

  def recv_tupobj(self, src):
    from aggregate_types import TupleType, ElementGetter
    assert src is self.tupobj
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      if obj.is_type(TupleType.get_typeobj()) and obj.elements != None:
        if len(obj.elements) != len(self.elements):
          self.raise_expt(ValueErrorType.occur('tuple unpackable: len(%r) != %r' % (obj, len(self.elements))))
        else:
          for (src,dest) in zip(obj.elements, self.elements):
            src.connect(dest)
      else:
        try:
          elemall = ElementGetter(obj, self)
          for dest in self.elements:
            elemall.connect(dest)
        except (NodeTypeError, NodeAttrError):
          self.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
    return
