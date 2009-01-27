#!/usr/bin/env python

from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError
from exception import ExceptionRaiser, MustBeDefinedNode, \
     TypeErrorType, AttributeErrorType


##  FunCall
##
class FunCall(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, func, args, kwargs={}):
    self.func = func
    self.args = args
    self.kwargs = kwargs
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    func.connect(self, self.recv_func)
    return

  def __repr__(self):
    return ('<call %r(%s)>' %
            (self.func, ', '.join(map(repr, self.args) +
                                  [ '%s=%r' % (k,v) for (k,v) in self.kwargs.iteritems() ])))

  def recv_func(self, src):
    for obj in src:
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
    MustBeDefinedNode.__init__(self, parent_frame, loc)
    target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return '%r.%s' % (self.target, self.attrname)

  def recv_target(self, src):
    for obj in src:
      try:
        obj.get_attr(self.attrname).connect(self)
      except NodeAttrError:
        self.raise_expt(AttributeErrorType.occur(
          'cannot get attribute: %r might be %r, no attr %s.' % (self.target, obj, self.attrname)))
    return

  def undefined(self):
    return AttributeErrorType.occur('attribute not defined: %r.%s' % (self.target, self.attrname))


##  AttrAssign
##
class AttrAssign(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, attrname, value):
    self.target = target
    self.attrname = attrname
    self.value = value
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r.%s, %r)' % (self.target, self.attrname, self.value)

  def recv_target(self, src):
    for obj in src:
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
    self.op = op
    self.left = left
    self.right = right
    self.done = set()
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    left.connect(self)
    right.connect(self)
    return
  
  def __repr__(self):
    return '%s(%r,%r)' % (self.op, self.left, self.right)

  VALID_TYPES = {
    ('str', 'Mul', 'int'): 'str',
    ('int', 'Mul', 'str'): 'str',
    ('unicode', 'Mul', 'int'): 'unicode',
    ('int', 'Mul', 'unicode'): 'unicode',
    }
  def recv(self, _):
    from builtin_types import BUILTIN_OBJECTS, NumberType, IntType, BaseStringType
    from aggregate_types import ListType, ListObject, TupleType, TupleObject
    for lobj in self.left:
      for robj in self.right:
        if (lobj,robj) in self.done: continue
        self.done.add((lobj,robj))
        # special handling for a formatting (%) operator
        ltype = lobj.get_type()
        rtype = robj.get_type()
        if (lobj.is_type(BaseStringType.get_typeobj()) and
            self.op == 'Mod'):
          self.update_types([lobj])
          continue
        # for numeric operation, the one with a higher rank is chosen.
        if (lobj.is_type(NumberType.get_typeobj()) and robj.is_type(NumberType.get_typeobj()) and
            self.op in ('Add','Sub','Mul','Div','Mod','FloorDiv','Power')):
          if ltype.get_rank() < rtype.get_rank():
            self.update_types([robj])
          else:
            self.update_types([lobj])
          continue
        if (lobj.is_type(IntType.get_typeobj()) and robj.is_type(IntType.get_typeobj()) and
            self.op in ('Bitand','Bitor','Bitxor')):
          self.update_types([robj])
          continue
        # for string operation, only Add is supported.
        if (lobj.is_type(BaseStringType.get_typeobj()) and robj.is_type(BaseStringType.get_typeobj()) and
            self.op == 'Add'):
          self.update_types([lobj])
          continue
        # for list operation, only Add and Mul is supported.
        if (lobj.is_type(ListType.get_typeobj()) and robj.is_type(ListType.get_typeobj()) and
            self.op == 'Add'):
          self.update_types([ListObject.concat(lobj, robj)])
          continue
        if (lobj.is_type(ListType.get_typeobj()) and robj.is_type(IntType.get_typeobj()) and
            self.op == 'Mul'):
          self.update_types([ListObject.multiply(lobj)])
          continue
        if (lobj.is_type(IntType.get_typeobj()) and robj.is_type(ListType.get_typeobj()) and
            self.op == 'Mul'):
          self.update_types([ListObject.multiply(robj)])
          continue
        # for tuple operation, only Add and Mul is supported.
        if (lobj.is_type(TupleType.get_typeobj()) and robj.is_type(TupleType.get_typeobj()) and
            self.op == 'Add'):
          self.update_types([TupleObject.concat(lobj, robj)])
          continue
        if (lobj.is_type(TupleType.get_typeobj()) and robj.is_type(IntType.get_typeobj()) and
            self.op == 'Mul'):
          self.update_types([TupleObject.multiply(lobj)])
          continue
        if (lobj.is_type(IntType.get_typeobj()) and robj.is_type(TupleType.get_typeobj()) and
            self.op == 'Mul'):
          self.update_types([TupleObject.multiply(robj)])
          continue
        # other operations.
        k = (ltype.get_name(), self.op, rtype.get_name())
        if k in self.VALID_TYPES:
          v = BUILTIN_OBJECTS[self.VALID_TYPES[k]]
          self.update_types([v])
          continue
        self.raise_expt(TypeErrorType.occur(
          'unsupported operand %s for %r and %r' % (self.op, lobj, robj)))
    return
  
  def undefined(self):
    return TypeErrorType.occur('unsupported operand %s for %r and %r' % (self.op, self.left, self.right))


##  AssignOp
##
class AssignOp(BinaryOp):

  BINOP = {
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
    }
  
  def __init__(self, parent_frame, loc, op, left, right):
    BinaryOp.__init__(self, parent_frame, loc, self.BINOP[op], left, right)
    self.connect(left)
    return


##  UnaryOp
##
class UnaryOp(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, op, value):
    self.value = value
    if op == 'UnaryAdd':
      self.op = '+'
    else:
      self.op = '-'
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.value.connect(self) # XXX handle optional methods
    return
  
  def __repr__(self):
    return '%s%r' % (self.op, self.value)
  

##  CompareOp
##
class CompareOp(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, expr0, comps):
    from builtin_types import BoolType
    self.expr0 = expr0
    self.comps = comps
    CompoundTypeNode.__init__(self, [BoolType.get_object()])
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.expr0.connect(self)
    for (_,expr) in self.comps:
      expr.connect(self)
    return
  
  def __repr__(self):
    return 'cmp(%r %s)' % (self.expr0,
                           ', '.join( '%s %r' % (op,expr) for (op,expr) in self.comps ))
  
  def recv(self, _):
    # ignore because CompareOp always returns bool.
    return


##  BooleanOp
##
class BooleanOp(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, op, nodes):
    from builtin_types import BoolType
    self.op = op
    self.nodes = nodes
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    if op != 'Or' or not [ 1 for node in nodes if isinstance(node, SimpleTypeNode) ]:
      BoolType.get_object().connect(self)
    for node in self.nodes:
      node.connect(self)
    return
  
  def __repr__(self):
    return '%s(%s)' % (self.op, ','.join(map(repr, self.nodes)))


##  NotOp
##
class NotOp(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, value):
    from builtin_types import BoolType
    self.value = value
    CompoundTypeNode.__init__(self, [BoolType.get_object()])
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.value.connect(self)
    return
  
  def __repr__(self):
    return 'not %r' % (self.value)
  
  def recv(self, _):
    # ignore because NotOp always returns bool.
    return


##  IfExpOp
##
class IfExpOp(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, test, then, else_):
    self.test = test
    self.then = then
    self.else_ = else_
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    then.connect(self)
    else_.connect(self)
    return
  
  def __repr__(self):
    return '%r if %r else %r' % (self.then, self.test, self.else_)


##  SubRef
##
class SubRef(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, subs):
    self.target = target
    self.subs = subs
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return '%r[%s]' % (self.target, ':'.join(map(repr, self.subs)))

  def recv_target(self, src):
    for obj in src:
      try:
        obj.get_element(self, self.subs).connect(self)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


##  SubAssign
##
class SubAssign(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, subs, value):
    self.target = target
    self.subs = subs
    self.value = value
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r%r, %r)' % (self.target, self.subs, self.value)

  def recv_target(self, src):
    for obj in src:
      try:
        self.value.connect(obj.get_element(self, self.subs, write=True))
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


##  IterRef
##
class IterRef(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target):
    self.target = target
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'iter(%r)' % (self.target,)

  def recv_target(self, src):
    for obj in src:
      try:
        obj.get_seq(self).connect(self)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('%r is not an iterator: %r' % (self.target, obj)))
    return


##  SliceRef
##
class SliceRef(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, lower, upper):
    self.target = target
    self.lower = lower
    self.upper = upper
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
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
    for obj in src:
      try:
        obj.get_element(self, [self.lower, self.upper]).connect(self)
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


##  SliceAssign
##
class SliceAssign(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, lower, upper, value):
    self.target = target
    self.lower = lower
    self.upper = upper
    self.value = value
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r[%r:%r], %r)' % (self.target, self.lower, self.upper, self.value)

  def recv_target(self, src):
    for obj in src:
      try:
        self.value.connect(obj.get_element(self, [self.lower, self.upper], write=True))
      except NodeTypeError:
        self.raise_expt(TypeErrorType.occur('unsubscriptable object: %r' % obj))
    return


##  TupleUnpack
##
class TupleUnpack(CompoundTypeNode, ExceptionRaiser):

  ##  Element
  ##
  class Element(CompoundTypeNode):
    
    def __init__(self, tup, i):
      CompoundTypeNode.__init__(self)
      self.tup = tup
      self.i = i
      return

    def __repr__(self):
      return '<TupleElement: %r[%d]>' % (self.tup, self.i)
  
  #
  def __init__(self, parent_frame, loc, tupobj, nelements):
    self.tupobj = tupobj
    self.elements = [ self.Element(self, i) for i in xrange(nelements) ]
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.tupobj.connect(self, self.recv_tupobj)
    return

  def __repr__(self):
    return '<TupleUnpack: %r>' % (self.tupobj,)

  def get_nth(self, i):
    return self.elements[i]

  def recv_tupobj(self, src):
    from aggregate_types import TupleType
    assert src is self.tupobj
    for obj in src:
      if obj.is_type(TupleType.get_typeobj()) and obj.elements != None:
        if len(obj.elements) != len(self.elements):
          self.raise_expt(ValueErrorType.occur('tuple unpackable: len(%r) != %r' % (obj, len(self.elements))))
        else:
          for (src,dest) in zip(obj.elements, self.elements):
            src.connect(dest)
      else:
        try:
          src = obj.get_seq(self)
          for dest in self.elements:
            src.connect(dest)
        except NodeTypeError:
          self.raise_expt(TypeErrorType.occur('not iterable: %r' % src))
    return