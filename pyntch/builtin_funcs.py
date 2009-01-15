#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import SimpleTypeNode, CompoundTypeNode
from exception import ExceptionType, ExceptionRaiser, TypeChecker
from namespace import Namespace
from function import ClassType, InstanceType
from builtin_types import NumberType, BoolType, IntType, LongType, StrType, ListObject, \
     BuiltinFunc, BuiltinConstFunc, BaseStringType, ANY_TYPE


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


##  RangeFunc
##
class RangeFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'range', ListObject([IntType.get_object()]), 
                         [IntType()],
                         [IntType(), IntType()])
    return


