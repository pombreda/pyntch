#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import CompoundTypeNode, NodeTypeError, NodeAttrError, UndefinedTypeNode
from typenode import BuiltinType, BuiltinCallable, BuiltinConstCallable
from exception import TypeChecker, SequenceTypeChecker
from basic_types import TypeType, NoneType, NumberType, BoolType, IntType, LongType, \
     FloatType, BaseStringType, StrType, UnicodeType, ANY
from aggregate_types import ListType, TupleType, DictType, IterType, ListObject
from expression import IterElement, IterRef, BinaryOp, MustBeDefinedNode, FunCall
from config import ErrorConfig


##  BuiltinFunc
class BuiltinFunc(BuiltinCallable, BuiltinType):

  TYPE_NAME = 'builtinfunc'
  
  def __init__(self, name, args=None, optargs=None, expts=None):
    BuiltinCallable.__init__(self, name, args=args, optargs=optargs, expts=expts)
    BuiltinType.__init__(self)
    return
  
  def __repr__(self):
    return '<builtin %s>' % self.name


##  BuiltinFuncNoKwd
class BuiltinFuncNoKwd(BuiltinFunc):

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(ErrorConfig.NoKeywordArgs())
      return UndefinedTypeNode()
    return self.process_args_nokwd(frame, args)

  def process_args_nokwd(self, frame, args):
    raise NotImplementedError


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
        self.frame.raise_expt(ErrorConfig.NotCallable(obj))
    return


##  AbsFunc
##
class AbsFunc(BuiltinFuncNoKwd):

  def __init__(self):
    BuiltinFunc.__init__(self, 'abs', [NumberType])
    return

  def process_args_nokwd(self, frame, args):
    checker = TypeChecker(frame, [NumberType.get_typeobj()], 'arg 0')
    args[0].connect(checker.recv)
    return args[0]


##  ApplyFunc
##
class ApplyFunc(BuiltinFuncNoKwd):

  def __init__(self):
    BuiltinFunc.__init__(self, 'apply', [ANY])
    return

  def process_args_nokwd(self, frame, args):
    star = dstar = None
    if 1 <= len(args):
      star = args[1]
    if 2 <= len(args):
      dstar = args[2]
    return FunCall(frame, args[0], star=star, dstar=dstar)


##  AllFunc, AnyFunc
##
class AllFunc(BuiltinConstFunc):

  def __init__(self, name='all'):
    BuiltinConstFunc.__init__(self, name, BoolType.get_object(), [ANY])
    return

  def accept_arg(self, frame, i, arg1):
    IterElement(frame, arg1)
    return 

class AnyFunc(AllFunc):

  def __init__(self):
    AllFunc.__init__(self, 'any')
    return


##  CallableFunc
##
class CallableFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'callable', BoolType.get_object(), [ANY])
    return


##  ChrFunc
##
class ChrFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'chr', StrType.get_object(),
                              [IntType])
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


##  DivmodFunc
##
class DivmodFunc(BuiltinFuncNoKwd):

  def __init__(self):
    BuiltinFunc.__init__(self, 'divmod', [NumberType, NumberType])
    return

  def process_args_nokwd(self, frame, args):
    checker = TypeChecker(frame, [NumberType.get_typeobj()], 'arg 0')
    args[0].connect(checker.recv)
    checker = TypeChecker(frame, [NumberType.get_typeobj()], 'arg 1')
    args[1].connect(checker.recv)
    obj = CompoundTypeNode(args)
    return TupleType.create_tuple([obj, obj])


##  FilterFunc
##
class FilterFunc(BuiltinFuncNoKwd):

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
            obj.call(self.frame, [self.elem], {})
          except NodeTypeError:
            self.frame.raise_expt(ErrorConfig.NotCallable(obj))
      return
      
  def __init__(self):
    BuiltinFunc.__init__(self, 'filter', [ANY, ANY])
    return

  def process_args_nokwd(self, frame, args):
    return self.FilterCaller(frame, args[0], args[1])


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


##  IterFunc
##
class IterFunc(BuiltinFuncNoKwd):

  def process_args_nokwd(self, frame, args):
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


##  LenFunc
##
class LenFunc(BuiltinFuncNoKwd):

  class LengthChecker(MustBeDefinedNode):
    
    def __init__(self, frame, target):
      self.done = set()
      self.target = target
      MustBeDefinedNode.__init__(self, frame)
      self.target.connect(self.recv_target)
      return

    def recv_target(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        try:
          obj.get_length(self.frame).connect(self.recv)
        except (NodeTypeError, NodeAttrError):
          pass
      return

    def check_undefined(self):
      if not self.types:
        self.raise_expt(ErrorConfig.NoLength(self.target))
      return

  def process_args_nokwd(self, frame, args):
    self.LengthChecker(frame, args[0])
    return IntType.get_object()
  
  def __init__(self):
    BuiltinFunc.__init__(self, 'len', [ANY])
    return


##  MapFunc
##
class MapFunc(BuiltinFuncNoKwd):

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
          obj.call(self.frame, self.args, {}).connect(self.listobj.elemall.recv)
        except NodeTypeError:
          self.frame.raise_expt(ErrorConfig.NotCallable(obj))
      return
      
  def __init__(self):
    BuiltinFunc.__init__(self, 'map', [ANY, ANY])
    return

  def process_args_nokwd(self, frame, args):
    return self.MapCaller(frame, args[0], args[1:])


##  MinFunc, MaxFunc
##
class MinFunc(BuiltinFunc):

  def __init__(self, name='min'):
    BuiltinFunc.__init__(self, name, [ANY])
    return

  def process_args(self, frame, args, kwargs):
    retobj = CompoundTypeNode()
    if len(args) == 1:
      IterElement(frame, args[0]).connect(retobj.recv)
    else:
      for arg1 in args:
        arg1.connect(retobj.recv)
    if 'key' in kwargs:
      IterFuncChecker(frame, retobj, kwargs['key'])
    return retobj
  
class MaxFunc(MinFunc):

  def __init__(self):
    MinFunc.__init__(self, 'max')
    return


##  OctFunc
##
class OctFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'oct', StrType.get_object(), [IntType])
    return


##  OrdFunc
##
class OrdFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'ord', IntType.get_object(),
                              [BaseStringType])
    return


##  PowFunc
##
class PowFunc(BuiltinFuncNoKwd):

  def __init__(self):
    BuiltinFunc.__init__(self, 'pow', [NumberType, NumberType], [NumberType])
    return

  def process_args_nokwd(self, frame, args):
    checker = TypeChecker(frame, [NumberType.get_typeobj()], 'arg 0')
    args[0].connect(checker.recv)
    checker = TypeChecker(frame, [NumberType.get_typeobj()], 'arg 1')
    args[1].connect(checker.recv)
    if 3 <= len(args):
      checker = TypeChecker(frame, [NumberType.get_typeobj()], 'arg 2')
      args[2].connect(checker.recv)
    return CompoundTypeNode(args)


##  RangeFunc
##
class RangeFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'range', ListType.create_list(IntType.get_object()), 
                              [IntType],
                              [IntType, IntType])
    return


##  RawInputFunc
##
class RawInputFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'raw_input', StrType.get_object(), [StrType])
    return


##  ReduceFunc
##
class ReduceFunc(BuiltinFuncNoKwd):

  class ReduceCaller(CompoundTypeNode):
    
    def __init__(self, frame, func, seq, initial):
      self.frame = frame
      self.done = set()
      self.elem = IterElement(frame, seq)
      self.result = CompoundTypeNode()
      if initial:
        initial.connect(self.result.recv)
      else:
        self.elem.connect(self.result.recv)
      self.args = (self.result, self.elem)
      CompoundTypeNode.__init__(self, [self.result])
      func.connect(self.recv_func)
      return

    def recv_func(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        try:
          result = obj.call(self.frame, self.args, {})
          result.connect(self.recv)
          result.connect(self.result.recv)
        except NodeTypeError:
          self.frame.raise_expt(ErrorConfig.NotCallable(obj))
      return
      
  def __init__(self):
    BuiltinFunc.__init__(self, 'reduce', [ANY, ANY])
    return

  def process_args_nokwd(self, frame, args):
    initial = None
    if 3 <= len(args):
      initial = args[2]
    return self.ReduceCaller(frame, args[0], args[1], initial)


##  ReprFunc
##
class ReprFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'repr', StrType.get_object(), [ANY])
    return


##  RoundFunc
##
class RoundFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'round', FloatType.get_object(),
                              [NumberType],
                              [IntType])
    return


##  SortedFunc
##
class SortedFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'sorted', [ANY])
    return

  def process_args(self, frame, args, kwargs):
    seq = ListType.create_list(elemall=IterElement(frame, args[0]))
    ListObject.SortMethod('sorted', seq).process_args(frame, args[1:], kwargs)
    return seq


##  SumFunc
##
class SumFunc(BuiltinFuncNoKwd):

  class SumCaller(CompoundTypeNode):
    
    def __init__(self, frame, seq, initial):
      self.frame = frame
      self.done = set()
      self.elem = IterElement(frame, seq)
      self.result = CompoundTypeNode()
      if initial:
        initial.connect(self.result.recv)
      else:
        self.elem.connect(self.result.recv)
      CompoundTypeNode.__init__(self, [self.result])
      IterElement(frame, seq).connect(self.recv_elem)
      return

    def recv_elem(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        BinaryOp(self.frame, 'Add', obj, self.result).connect(self.result.recv)
      return
  
  def __init__(self):
    BuiltinFunc.__init__(self, 'sum', [ANY], [ANY])
    return

  def process_args_nokwd(self, frame, args):
    initial = None
    if 2 <= len(args):
      initial = args[1]
    return self.SumCaller(frame, args[0], initial)


##  UnichrFunc
##
class UnichrFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'unichr', UnicodeType.get_object(),
                              [IntType])
    return


##  ZipFunc
##
class ZipFunc(BuiltinFuncNoKwd):

  def __init__(self):
    BuiltinFunc.__init__(self, 'zip')
    return

  def process_args_nokwd(self, frame, args):
    elems = [ CompoundTypeNode() for arg1 in args ]
    zipelem = TupleType.create_tuple(elements=elems)
    seq = ListType.create_list(elemall=zipelem)
    for (i,arg1) in enumerate(args):
      IterElement(frame, arg1).connect(elems[i].recv)
    return seq
