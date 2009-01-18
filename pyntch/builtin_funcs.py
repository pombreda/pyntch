#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError
from exception import ExceptionType, ExceptionRaiser, TypeChecker
from namespace import Namespace
from function import ClassType, InstanceType
from builtin_types import NumberType, BoolType, IntType, LongType, \
     BaseStringType, StrType, UnicodeType, ANY_TYPE, \
     BuiltinFunc, BuiltinConstFunc
from aggregate_types import ListObject, TupleObject, IterObject


##  ReprFunc
##
class ReprFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'repr', StrType.get_object(),
                         [ANY_TYPE])
    return


##  LenFunc
##
class LenFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'len', IntType.get_object(),
                              [ANY_TYPE])
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


##  IterFunc
##
class IterFunc(BuiltinFunc):

  class IterConversion(CompoundTypeNode, ExceptionRaiser):
    
    def __init__(self, parent_frame, loc):
      CompoundTypeNode.__init__(self)
      ExceptionRaiser.__init__(self, parent_frame, loc)
      return
    
    def recv(self, src):
      for obj in src.types:
        try:
          self.update_types(set([IterObject(elemall=obj.get_iter(self))]))
        except NodeTypeError:
          self.raise_expt(ExceptionType(
            'TypeError',
            '%r is not iterable: %r' % (src, obj)))
      return
  
  def process_args(self, caller, args):
    iterobj = self.IterConversion(caller, caller.loc)
    args[0].connect(iterobj)
    return iterobj

  def __init__(self):
    BuiltinFunc.__init__(self, 'iter', [ANY_TYPE])


##  RangeFunc
##
class RangeFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'range', ListObject([IntType.get_object()]), 
                         [IntType()],
                         [IntType(), IntType()])
    return


