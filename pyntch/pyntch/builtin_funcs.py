#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import CompoundTypeNode, NodeTypeError, NodeAttrError, BuiltinType
from frame import MustBeDefinedNode
from exception import TypeChecker, SequenceTypeChecker
from exception import TypeErrorType
from namespace import Namespace
from klass import InstanceObject
from basic_types import TypeType, NoneType, NumberType, BoolType, IntType, LongType, FloatType, \
     BaseStringType, StrType, UnicodeType, ANY, \
     BuiltinCallable, BuiltinConstCallable
from aggregate_types import ListType, TupleType, DictType, IterType, ListObject
from expression import IterElement, BinaryOp


##  BuiltinFunc
class BuiltinFunc(BuiltinCallable, BuiltinType):

  TYPE_NAME = 'builtinfunc'
  
  def __init__(self, name, args=None, optargs=None, expts=None):
    BuiltinCallable.__init__(self, name, args=args, optargs=optargs, expts=expts)
    BuiltinType.__init__(self)
    return
  
  def __repr__(self):
    return '<builtin %s>' % self.name


##  BuiltinConstFunc
class BuiltinConstFunc(BuiltinConstCallable, BuiltinType):

  TYPE_NAME = 'builtinfunc'

  def __init__(self, name, retobj, args=None, optargs=None, expts=None):
    BuiltinType.__init__(self)
    BuiltinConstCallable.__init__(self, name, retobj, args=args, optargs=optargs, expts=expts)
    return
  
  def __repr__(self):
    return '<builtin %s>' % self.name


##  IterFuncChecker
class IterFuncChecker(CompoundTypeNode):

  def __init__(self, frame, target, func):
    self.frame = frame
    self.target = target
    CompoundTypeNode.__init__(self)
    func.connect(self.recv_func)
    return

  def recv_func(self, src):
    for obj in src:
      try:
        obj.call(self.frame, [self.target.elemall])
      except NodeTypeError:
        self.frame.raise_expt(TypeErrorType.occur('function not callable:' % obj))
    return


##  ReprFunc
##
class ReprFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'repr', StrType.get_object(), [ANY])
    return


##  LenFunc
##
class LenFunc(BuiltinFunc):

  class LengthChecker(MustBeDefinedNode):
    
    def __init__(self, frame, target):
      self.done = set()
      self.target = target
      MustBeDefinedNode.__init__(self, frame)
      self.target.connect(self.recv_target)
      return

    def recv_target(self, src):
      from expression import MethodCall
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        if obj.is_type(ListType.get_typeobj(), TupleType.get_typeobj(), DictType.get_typeobj()):
          obj.connect(self)
        elif isinstance(obj, InstanceObject):
          MethodCall(self, obj, '__len__').connect(self)
      return

    def check_undefined(self):
      if not self.types:
        self.raise_expt(TypeErrorType.occur('__len__ not defined: %r' % (self.target)))
      return

  def process_args(self, frame, args, kwargs):
    self.LengthChecker(frame, args[0])
    return IntType.get_object()
  
  def __init__(self):
    BuiltinFunc.__init__(self, 'len', [ANY])
    return


##  ChrFunc
##
class ChrFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'chr', StrType.get_object(),
                              [IntType])
    return


##  UnichrFunc
##
class UnichrFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'unichr', UnicodeType.get_object(),
                              [IntType])
    return


##  OrdFunc
##
class OrdFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'ord', IntType.get_object(),
                              [BaseStringType])
    return


##  RangeFunc
##
class RangeFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'range', ListType.create_list(IntType.get_object()), 
                              [IntType],
                              [IntType, IntType])
    return


##  CallableFunc
##
class CallableFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'callable', BoolType.get_object(), [ANY])
    return


##  CmpFunc
##
class CmpFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'cmp', IntType.get_object(), [ANY, ANY])
    return


##  DirFunc
##
class DirFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'dir', ListType.create_list(StrType.get_object()), [], [ANY])
    return


##  HashFunc
##
class HashFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'hash', IntType.get_object(), [ANY])
    return


##  HexFunc
##
class HexFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'hex', StrType.get_object(), [IntType])
    return


##  IdFunc
##
class IdFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'id', IntType.get_object(), [ANY])
    return


##  IsInstanceFunc
##
class IsInstanceFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'isinstance', BoolType.get_object(), [ANY, TypeType])
    return


##  IsSubclassFunc
##
class IsSubclassFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'issubclass', BoolType.get_object(), [TypeType, TypeType])
    return


##  OctFunc
##
class OctFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'oct', StrType.get_object(), [IntType])
    return


##  RawInputFunc
##
class RawInputFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'raw_input', StrType.get_object(), [StrType])
    return


##  RoundFunc
##
class RoundFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'round', FloatType.get_object(),
                              [NumberType],
                              [IntType])
    return


##  IterFunc
##
class IterFunc(BuiltinFunc):

  def process_args(self, frame, args, kwargs):
    from expression import IterRef
    v = args[0]
    if v in self.cache:
      iterobj = self.cache[v]
    else:
      iterobj = IterRef(frame, v)
      self.cache[v] = iterobj
    return iterobj

  def __init__(self):
    self.cache = {}
    BuiltinFunc.__init__(self, 'iter', [ANY])
    return


##  AbsFunc
##
class AbsFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'abs', [NumberType])
    return

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
      return UndefinedTypeNode()
    args[0].connect(TypeChecker(frame, [NumberType.get_typeobj()], 'arg0'))
    return args[0]


##  DivmodFunc
##
class DivmodFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'divmod', [NumberType, NumberType])
    return

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
      return UndefinedTypeNode()
    args[0].connect(TypeChecker(frame, [NumberType.get_typeobj()], 'arg0'))
    args[1].connect(TypeChecker(frame, [NumberType.get_typeobj()], 'arg1'))
    obj = CompoundTypeNode(args)
    return TupleType.create_tuple([obj, obj])


##  PowFunc
##
class PowFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'pow', [NumberType, NumberType], [NumberType])
    return

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
      return UndefinedTypeNode()
    args[0].connect(TypeChecker(frame, [NumberType.get_typeobj()], 'arg0'))
    args[1].connect(TypeChecker(frame, [NumberType.get_typeobj()], 'arg1'))
    if 3 <= len(args):
      args[2].connect(TypeChecker(frame, [NumberType.get_typeobj()], 'arg2'))
    return CompoundTypeNode(args)


##  AllFunc, AnyFunc
##
class AllFunc(BuiltinConstFunc):

  def __init__(self, name='all'):
    BuiltinConstFunc.__init__(self, name, BoolType.get_object(), [ANY])
    return

  def accept_arg(self, frame, i, arg1):
    from expression import IterElement
    IterElement(frame, arg1)
    return 

class AnyFunc(AllFunc):

  def __init__(self):
    AllFunc.__init__(self, 'any')
    return


##  MinFunc, MaxFunc
##
class MinFunc(BuiltinFunc):

  def __init__(self, name='min'):
    BuiltinFunc.__init__(self, name, [ANY])
    return

  def process_args(self, frame, args, kwargs):
    from expression import IterElement
    retobj = CompoundTypeNode()
    if len(args) == 1:
      IterElement(frame, args[0]).connect(retobj)
    else:
      for arg1 in args:
        arg1.connect(retobj)
    if 'key' in kwargs:
      IterFuncChecker(frame, retobj, kwargs['key'])
    return retobj
  
class MaxFunc(MinFunc):

  def __init__(self):
    MinFunc.__init__(self, 'max')
    return


##  MapFunc
##
class MapFunc(BuiltinFunc):

  class MapCaller(CompoundTypeNode):
    
    def __init__(self, frame, func, objs):
      self.frame = frame
      self.done = set()
      self.args = [ IterElement(frame, obj) for obj in objs ]
      self.listobj = ListType.create_list()
      CompoundTypeNode.__init__(self, [self.listobj])
      func.connect(self.recv_func)
      return

    def recv_func(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        try:
          obj.call(self.frame, self.args, {}, None, None).connect(self.listobj.elemall)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('function not callable:' % obj))
      return
      
  def __init__(self):
    BuiltinFunc.__init__(self, 'map', [ANY, ANY])
    return

  def call(self, frame, args, kwargs, star, dstar):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
      return UndefinedTypeNode()
    if len(args) < self.minargs:
      frame.raise_expt(TypeErrorType.occur(
        'too few argument for %s: %d or more.' % (self.name, self.minargs)))
      return UndefinedTypeNode()
    return self.MapCaller(frame, args[0], args[1:])


##  ReduceFunc
##
class ReduceFunc(BuiltinFunc):

  class ReduceCaller(CompoundTypeNode):
    
    def __init__(self, frame, func, seq, initial):
      self.frame = frame
      self.done = set()
      self.elem = IterElement(frame, seq)
      self.result = CompoundTypeNode()
      if initial:
        initial.connect(self.result)
      else:
        self.elem.connect(self.result)
      self.args = (self.result, self.elem)
      CompoundTypeNode.__init__(self, [self.result])
      func.connect(self.recv_func)
      return

    def recv_func(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        try:
          result = obj.call(self.frame, self.args, {}, None, None)
          result.connect(self)
          result.connect(self.result)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('function not callable:' % obj))
      return
      
  def __init__(self):
    BuiltinFunc.__init__(self, 'reduce', [ANY, ANY])
    return

  def call(self, frame, args, kwargs, star, dstar):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
      return UndefinedTypeNode()
    if len(args) < self.minargs:
      frame.raise_expt(TypeErrorType.occur(
        'too few argument for %s: %d or more.' % (self.name, self.minargs)))
      return UndefinedTypeNode()
    initial = None
    if 3 <= len(args):
      initial = args[2]
    return self.ReduceCaller(frame, args[0], args[1], initial)


##  FilterFunc
##
class FilterFunc(BuiltinFunc):

  class FilterCaller(CompoundTypeNode):
    
    def __init__(self, frame, func, seq):
      self.frame = frame
      self.done = set()
      self.elem = IterElement(frame, seq)
      CompoundTypeNode.__init__(self, [seq])
      func.connect(self.recv_func)
      return

    def recv_func(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        if not isinstance(obj, NoneType):
          try:
            obj.call(self.frame, [self.elem], {}, None, None)
          except NodeTypeError:
            self.frame.raise_expt(TypeErrorType.occur('function not callable:' % obj))
      return
      
  def __init__(self):
    BuiltinFunc.__init__(self, 'filter', [ANY, ANY])
    return

  def call(self, frame, args, kwargs, star, dstar):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
      return UndefinedTypeNode()
    if len(args) < self.minargs:
      frame.raise_expt(TypeErrorType.occur(
        'too few argument for %s: %d or more.' % (self.name, self.minargs)))
      return UndefinedTypeNode()
    return self.FilterCaller(frame, args[0], args[1])


##  SumFunc
##
class SumFunc(BuiltinFunc):

  class SumCaller(CompoundTypeNode):
    
    def __init__(self, frame, seq, initial):
      self.frame = frame
      self.done = set()
      self.elem = IterElement(frame, seq)
      self.result = CompoundTypeNode()
      if initial:
        initial.connect(self.result)
      else:
        self.elem.connect(self.result)
      CompoundTypeNode.__init__(self, [self.result])
      IterElement(frame, seq).connect(self.recv_elem)
      return

    def recv_elem(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        BinaryOp(self.frame, 'Add', obj, self.result).connect(self.result)
      return
  
  def __init__(self):
    BuiltinFunc.__init__(self, 'sum', [ANY], [ANY])
    return

  def call(self, frame, args, kwargs, star, dstar):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
      return UndefinedTypeNode()
    if len(args) < self.minargs:
      frame.raise_expt(TypeErrorType.occur(
        'too few argument for %s: %d or more.' % (self.name, self.minargs)))
      return UndefinedTypeNode()
    initial = None
    if 2 <= len(args):
      initial = args[1]
    return self.SumCaller(frame, args[0], initial)


##  SortedFunc
##
class SortedFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'sorted', [ANY])
    return

  def call(self, frame, args, kwargs, star, dstar):
    if len(args) < self.minargs:
      frame.raise_expt(TypeErrorType.occur(
        'too few argument for %s: %d or more.' % (self.name, self.minargs)))
      return UndefinedTypeNode()
    seq = ListType.create_list(elemall=IterElement(frame, args[0]))
    ListObject.SortMethod('sorted', seq).process_args(frame, args[1:], kwargs)
    return seq


##  ZipFunc
##
class ZipFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'zip')
    return

  def call(self, frame, args, kwargs, star, dstar):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
      return UndefinedTypeNode()
    elems = [ CompoundTypeNode() for arg1 in args ]
    zipelem = TupleType.create_tuple(elements=elems)
    seq = ListType.create_list(elemall=zipelem)
    for (i,arg1) in enumerate(args):
      IterElement(frame, arg1).connect(elems[i])
    return seq
