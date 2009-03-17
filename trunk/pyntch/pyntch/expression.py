#!/usr/bin/env python

from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, NodeAssignError
from exception import TypeErrorType, AttributeErrorType, ValueErrorType
from frame import ExecutionFrame


##  ExpressionNode
##
class ExpressionNode(CompoundTypeNode):
  
  def __init__(self, frame):
    self.frame = frame
    CompoundTypeNode.__init__(self)
    return
  
  def raise_expt(self, expt):
    self.frame.raise_expt(expt)
    return


##  MustBeDefinedNode
##
class MustBeDefinedNode(ExpressionNode):

  nodes = None
  
  def __init__(self, frame):
    ExpressionNode.__init__(self, frame)
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


###  References
###

##  AttrRef
##
class AttrRef(MustBeDefinedNode):
  
  def __init__(self, frame, target, attrname):
    self.target = target
    self.attrname = attrname
    self.done = set()
    MustBeDefinedNode.__init__(self, frame)
    self.target.connect(self.recv_target)
    return

  def __repr__(self):
    return '%r.%s' % (self.target, self.attrname)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        obj.get_attr(self.attrname).connect(self.recv)
      except NodeAttrError:
        self.raise_expt(AttributeErrorType.occur('attribute not allowed: %r.%s.' % (obj, self.attrname)))
    return

  def check_undefined(self):
    if not self.types:
      self.raise_expt(AttributeErrorType.occur('attribute not defined: %r.%s.' % (self.target, self.attrname)))
    return


class OptAttrRef(ExpressionNode):
  
  def __init__(self, frame, target, attrname):
    self.target = target
    self.attrname = attrname
    self.done = set()
    ExpressionNode.__init__(self, frame)
    self.target.connect(self.recv_target)
    return

  def __repr__(self):
    return '%r.%s' % (self.target, self.attrname)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        obj.get_attr(self.attrname).connect(self.recv)
      except NodeAttrError:
        self.raise_expt(AttributeErrorType.occur('attribute not defined: %r.%s.' % (obj, self.attrname)))
    return


##  IterRef
##
class IterRef(ExpressionNode):
  
  def __init__(self, frame, target):
    self.target = target
    self.done = set()
    ExpressionNode.__init__(self, frame)
    self.target.connect(self.recv_target)
    return

  def __repr__(self):
    return 'iter(%r)' % (self.target,)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        obj.get_iter(self.frame).connect(self.recv)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
    return


##  SubRef
##
class SubRef(ExpressionNode):
  
  def __init__(self, frame, target, subs):
    self.target = target
    self.subs = subs
    self.done = set()
    ExpressionNode.__init__(self, frame)
    self.target.connect(self.recv_target)
    return

  def __repr__(self):
    return '%r[%s]' % (self.target, ':'.join(map(repr, self.subs)))

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        obj.get_element(self.frame, self.subs).connect(self.recv)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


##  SliceRef
##
class SliceRef(ExpressionNode):
  
  def __init__(self, frame, target, subs):
    self.target = target
    self.subs = subs
    self.done = set()
    ExpressionNode.__init__(self, frame)
    self.target.connect(self.recv_target)
    return

  def __repr__(self):
    return '%r%r' % (self.target, self.subs)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        obj.get_slice(self.frame, self.subs).connect(self.recv)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


###  Assignments
###

##  AttrAssign
##
class AttrAssign(ExpressionNode):
  
  def __init__(self, frame, target, attrname, value):
    self.target = target
    self.attrname = attrname
    self.value = value
    self.done = set()
    ExpressionNode.__init__(self, frame)
    self.target.connect(self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r.%s, %r)' % (self.target, self.attrname, self.value)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        self.value.connect(obj.get_attr(self.attrname, write=True).recv)
      except (NodeAttrError, NodeTypeError):
        self.raise_expt(AttributeErrorType.occur(
          'cannot assign attribute: %r might be %r, no attr %s' % (self.target, obj, self.attrname)))
      except NodeAssignError:
        self.raise_expt(AttributeErrorType.occur('cannot assign attribute: %r' % obj))
    return


##  SubAssign
##
class SubAssign(ExpressionNode):
  
  def __init__(self, frame, target, sub, value):
    self.target = target
    self.sub = sub
    self.value = value
    self.done = set()
    ExpressionNode.__init__(self, frame)
    self.target.connect(self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r[%r], %r)' % (self.target, self.sub, self.value)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        self.value.connect(obj.get_element(self.frame, self.sub, write=True).recv)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
      except NodeAssignError:
        self.raise_expt(TypeErrorType.occur('cannot assign item: %r' % obj))
    return


##  SliceAssign
##
class SliceAssign(ExpressionNode):
  
  def __init__(self, frame, target, subs, value):
    self.target = target
    self.subs = subs
    self.done = set()
    ExpressionNode.__init__(self, frame)
    self.elemall = IterElement(frame, value)
    self.target.connect(self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r%r, %r)' % (self.target, self.subs, self.target)

  def recv_target(self, src):
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        seq = obj.get_slice(self.frame, self.subs, write=True)
        self.elemall.connect(seq.elemall.recv)
      except (NodeTypeError, NodeAttrError):
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
      except NodeAssignError:
        self.raise_expt(TypeErrorType.occur('cannot assign item: %r' % obj))
    return


###  Operators
###

##  FunCall
##
class FunCall(ExpressionNode):
  
  def __init__(self, frame, func, args=None, kwargs=None, star=None, dstar=None):
    self.func = func
    self.args = args or ()
    self.kwargs = kwargs or {}
    self.star = star
    self.dstar = dstar
    self.done = set()
    assert isinstance(frame, ExecutionFrame)
    ExpressionNode.__init__(self, frame)
    func.connect(self.recv_func)
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
        obj.call(self.frame, self.args, self.kwargs, self.star, self.dstar).connect(self.recv)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('cannot call: %r might be %r' % (self.func, obj)))
    return


##  BinaryOp
##
class BinaryOp(MustBeDefinedNode):
  
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

  def __init__(self, frame, op, left, right):
    assert op in ('Add','Sub','Mul','Div','Mod','FloorDiv','Power',
                  'Bitand','Bitor','Bitxor','RightShift','LeftShift')
    self.op = op
    self.left = left
    self.right = right
    self.received = set()
    self.computed = set()
    self.tupleobj = self.listobj = None
    MustBeDefinedNode.__init__(self, frame)
    self.left.connect(self.recv_left)
    self.right.connect(self.recv_right)
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

  def update_op(self, lobj, robj):
    from basic_types import NumberType, IntType, BaseStringType, BUILTIN_OBJECT
    from aggregate_types import ListType, ListObject, TupleType
    from klass import InstanceObject
    if (lobj,robj) in self.received: return
    self.received.add((lobj,robj))
    # special handling for a formatting (%) operator
    ltype = lobj.get_type()
    rtype = robj.get_type()
    if (lobj.is_type(BaseStringType.get_typeobj()) and
        self.op == 'Mod'):
      self.computed.add((lobj,robj))
      lobj.connect(self.recv)
      return
    # for numeric operation, the one with a higher rank is chosen.
    if (lobj.is_type(NumberType.get_typeobj()) and robj.is_type(NumberType.get_typeobj()) and
        self.op in ('Add','Sub','Mul','Div','Mod','FloorDiv','Power','LeftShift','RightShift')):
      self.computed.add((lobj,robj))
      if ltype.get_rank() < rtype.get_rank():
        robj.connect(self.recv)
      else:
        lobj.connect(self.recv)
      return
    if (lobj.is_type(IntType.get_typeobj()) and robj.is_type(IntType.get_typeobj()) and
        self.op in ('Bitand','Bitor','Bitxor')):
      self.computed.add((lobj,robj))
      robj.connect(self.recv)
      return
    # for string operation, only Add is supported.
    if (lobj.is_type(BaseStringType.get_typeobj()) and robj.is_type(BaseStringType.get_typeobj()) and
        self.op == 'Add'):
      self.computed.add((lobj,robj))
      robj.connect(self.recv)
      return
    # adding lists.
    if (self.op == 'Add' and
        (lobj.is_type(ListType.get_typeobj()) and robj.is_type(ListType.get_typeobj()))):
      if not self.listobj:
        self.listobj = ListType.create_list()
        self.listobj.connect(self.recv)
      self.computed.add((lobj,robj))
      lobj.connect_element(self.listobj)
      robj.connect_element(self.listobj)
      return
    # multiplying a list by an integer.
    if self.op == 'Mul':
      if lobj.is_type(ListType.get_typeobj()) and robj.is_type(IntType.get_typeobj()):
        self.computed.add((lobj,robj))
        lobj.connect(self.recv)
        return
      elif lobj.is_type(IntType.get_typeobj()) and robj.is_type(ListType.get_typeobj()):
        self.computed.add((lobj,robj))
        robj.connect(self.recv)
        return
    # adding tuples.
    if (self.op == 'Add' and
        (lobj.is_type(TupleType.get_typeobj()) and robj.is_type(TupleType.get_typeobj()))):
      if not self.tupleobj:
        self.tupleobj = TupleType.create_tuple()
        self.tupleobj.connect(self.recv)
      self.computed.add((lobj,robj))
      lobj.connect_element(self.tupleobj)
      robj.connect_element(self.tupleobj)
      return
    # multiplying a tuple by an integer.
    if self.op == 'Mul':
      if lobj.is_type(TupleType.get_typeobj()) and robj.is_type(IntType.get_typeobj()):
        self.computed.add((lobj,robj))
        lobj.connect(self.recv)
        return
      elif lobj.is_type(IntType.get_typeobj()) and robj.is_type(TupleType.get_typeobj()):
        self.computed.add((lobj,robj))
        robj.connect(self.recv)
        return
    # other valid operations.
    k = (ltype.get_name(), self.op, rtype.get_name())
    if k in self.VALID_TYPES:
      self.computed.add((lobj,robj))
      BUILTIN_OBJECT[self.VALID_TYPES[k]].connect(self.recv)
      return
    # Handle optional methods.
    if isinstance(lobj, InstanceObject):
      result = MethodCall(self.frame, lobj, self.LMETHOD[self.op], [robj])
      result.connect(lambda src: self.recv_result(src, (lobj, robj)))
    if isinstance(robj, InstanceObject):
      result = MethodCall(self.frame, robj, self.RMETHOD[self.op], [lobj])
      result.connect(lambda src: self.recv_result(src, (lobj, robj)))
    return

  def recv_result(self, src, objs):
    self.computed.add(objs)
    return self.recv(src)
  
  def check_undefined(self):
    for (lobj,robj) in self.received:
      if (lobj,robj) not in self.computed:
        self.raise_expt(TypeErrorType.occur('unsupported operand %s for %s and %s' %
                                            (self.op, lobj.describe(), lobj.describe())))
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
  
  def __init__(self, frame, op, left, right):
    BinaryOp.__init__(self, frame, self.OPS[op], left, right)
    self.connect(left.recv)
    return


##  UnaryOp
##
class UnaryOp(MustBeDefinedNode):

  METHOD = {
    'UnaryAdd': '__pos__',
    'UnarySub': '__neg__',
    'Invert': '__invert__',
    }
  
  def __init__(self, frame, op, value):
    self.value = value
    self.op = op
    self.done = set()
    MustBeDefinedNode.__init__(self, frame)
    self.value.connect(self.recv_value)
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
        obj.connect(self.recv)
      elif isinstance(obj, InstanceObject):
        MethodCall(self.frame, obj, self.METHOD[self.op]).connect(self.recv)
    return


##  CompareOp
##
class CompareOp(ExpressionNode):

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
  
  def __init__(self, frame, op, left, right):
    from basic_types import BoolType
    self.op = op
    self.left = left
    self.right = right
    self.done = set()
    ExpressionNode.__init__(self, frame)
    BoolType.get_object().connect(self.recv)
    if op not in ('is', 'is not'):
      self.left.connect(self.recv_left)
    return
  
  def __repr__(self):
    return '%s(%r,%r)' % (self.op, self.left, self.right)

  def recv_left(self, left):
    from klass import InstanceObject
    for lobj in left:
      if lobj in self.done: continue
      self.done.add(lobj)
      if isinstance(lobj, InstanceObject):
        MethodCall(self.frame, lobj, self.LMETHOD[self.op], [self.right])
    return


##  BooleanOp
##
class BooleanOp(ExpressionNode):
  
  def __init__(self, frame, op, nodes):
    from basic_types import BoolType
    self.op = op
    self.nodes = nodes
    ExpressionNode.__init__(self, frame)
    if op == 'Or' and not [ 1 for node in nodes if isinstance(node, SimpleTypeNode) ]:
      BoolType.get_object().connect(self.recv)
    for node in self.nodes:
      node.connect(self.recv)
    return
  
  def __repr__(self):
    return '%s(%s)' % (self.op, ','.join(map(repr, self.nodes)))


##  NotOp
##
class NotOp(ExpressionNode):
  
  def __init__(self, frame, value):
    from basic_types import BoolType
    self.value = value
    ExpressionNode.__init__(self, frame)
    BoolType.get_object().connect(self.recv)
    self.value.connect(self.recv)
    return
  
  def __repr__(self):
    return 'not %r' % (self.value)
  
  def recv(self, _):
    # ignore because NotOp always returns bool.
    return


##  IfExpOp
##
class IfExpOp(ExpressionNode):
  
  def __init__(self, frame, test, then, else_):
    self.test = test
    self.then = then
    self.else_ = else_
    ExpressionNode.__init__(self, frame)
    self.then.connect(self.recv)
    self.else_.connect(self.recv)
    return
  
  def __repr__(self):
    return '%r if %r else %r' % (self.then, self.test, self.else_)


###  Syntax Sugar
###

##  MethodCall
##
def MethodCall(frame, target, name, args=None, kwargs=None, star=None, dstar=None):
  assert isinstance(frame, ExecutionFrame)
  return FunCall(frame, OptAttrRef(frame, target, name),
                 args=args, kwargs=kwargs, star=star, dstar=dstar)


##  IterElement
##
def IterElement(frame0, target):
  from frame import ExceptionCatcher
  from exception import StopIterationType
  frame1 = ExceptionCatcher(frame0)
  frame1.add_handler(StopIterationType.get_typeobj())
  return MethodCall(frame1, IterRef(frame0, target), 'next')


##  TupleUnpack
##
class TupleUnpack(ExpressionNode):

  def __init__(self, frame, tupobj, nelements, strict=True):
    self.tupobj = tupobj
    self.elements = [ CompoundTypeNode() for _ in xrange(nelements) ]
    self.strict = strict
    self.done = set()
    ExpressionNode.__init__(self, frame)
    self.tupobj.connect(self.recv_tupobj)
    return

  def __repr__(self):
    return '<TupleUnpack: %r (%d)>' % (self.tupobj, len(self.elements))

  def get_nth(self, i):
    return self.elements[i]

  def recv_tupobj(self, src):
    from aggregate_types import TupleType
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      if obj.is_type(TupleType.get_typeobj()) and obj.elements != None:
        # Unpack a fixed-length tuple.
        if (self.strict and len(obj.elements) != len(self.elements)) or len(obj.elements) < len(self.elements):
          self.raise_expt(ValueErrorType.occur('tuple unpackable: len(%r) != %r' % (obj, len(self.elements))))
        else:
          for (src,dest) in zip(obj.elements, self.elements):
            src.connect(dest.recv)
      else:
        # Unpack a variable-length tuple or other iterable.
        elemall = IterElement(self.frame, obj)
        for dest in self.elements:
          elemall.connect(dest.recv)
    return


##  TupleSlice
##
class TupleSlice(ExpressionNode):

  def __init__(self, frame, tupobj, start, end=None):
    self.tupobj = tupobj
    self.start = start
    if end == None:
      self.length = 0
    else:
      self.length = end-start+1
    self.done = set()
    ExpressionNode.__init__(self, frame)
    self.tupobj.connect(self.recv_tupobj)
    return

  def __repr__(self):
    if self.length:
      return '<TupleSlice: %r[%r:%r]>' % (self.tupobj, self.start, self.start+self.length-1)
    else:
      return '<TupleSlice: %r[%r:]>' % (self.tupobj, self.start)

  def recv_tupobj(self, src):
    from aggregate_types import TupleType
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      if obj.is_type(TupleType.get_typeobj()) and obj.elements != None:
        # Unpack a fixed-length tuple.
        if self.length:
          if self.length != len(obj.elements):
            self.raise_expt(ValueErrorType.occur('tuple unpackable: len(%r) != %r' % (obj, self.length)))
          else:
            for i in xrange(self.length):
              obj.elements[self.start+i].connect(self.recv)
        else:
          for i in xrange(self.start, len(obj.elements)):
            obj.elements[i].connect(self.recv)
      else:
        # Unpack a variable-length tuple or other iterable.
        IterElement(self.frame, obj).connect(self.recv)
    return
