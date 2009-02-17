#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, BuiltinType
from exception import TypeChecker, SequenceTypeChecker
from exception import TypeErrorType
from namespace import Namespace
from basic_types import TypeType, NumberType, BoolType, IntType, LongType, FloatType, \
     BaseStringType, StrType, UnicodeType, ANY, \
     BuiltinCallable, BuiltinConstCallable
from aggregate_types import ListType, TupleType, IterType, ElementGetter


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

  def __init__(self, name, retype, args=None, optargs=None, expts=None):
    BuiltinConstCallable.__init__(self, name, retype, args=args, optargs=optargs, expts=expts)
    BuiltinType.__init__(self)
    return
  
  def __repr__(self):
    return '<builtin %s>' % self.name


##  ReprFunc
##
class ReprFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'repr', StrType.get_object(),
                              [ANY])
    return


##  LenFunc
##
class LenFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'len', IntType.get_object(),
                              [ANY])
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

  class IterConversion(CompoundTypeNode):
    
    def __init__(self, frame, obj):
      self.frame = frame
      self.done = set()
      CompoundTypeNode.__init__(self)
      obj.connect(self, self.recv_elem)
      return
    
    def recv_elem(self, src):
      for obj in src:
        if obj in self.done: continue
        self.done.add(obj)
        try:
          obj.get_iter(self.frame).connect(self)
        except (NodeTypeError, NodeAttrError):
          self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
      return
  
  def process_args(self, frame, args, kwargs):
    v = args[0]
    if v in self.cache:
      iterobj = self.cache[v]
    else:
      iterobj = self.IterConversion(frame, v)
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
    args[0].connect(TypeChecker(frame, [NumberType.get_typeobj()], 'arg0'))
    args[1].connect(TypeChecker(frame, [NumberType.get_typeobj()], 'arg1'))
    if 3 <= len(args):
      args[2].connect(TypeChecker(frame, [NumberType.get_typeobj()], 'arg2'))
    return CompoundTypeNode(args)


##  AllFunc, AnyFunc
##
class AllFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'all', [ANY])
    return

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
    ElementGetter(args[0], frame)
    return BoolType.get_object()

class AnyFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'any', [ANY])
    return

  def process_args(self, frame, args, kwargs):
    if kwargs:
      frame.raise_expt(TypeErrorType.occur('cannot take keyword argument.'))
    ElementGetter(args[0], frame)
    return BoolType.get_object()


