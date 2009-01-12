#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import SimpleTypeNode, CompoundTypeNode
from exception import ExceptionType, ExceptionRaiser, TypeChecker
from namespace import Namespace
from function import ClassType, InstanceType
from builtin_types import NumberType, BoolType, IntType, LongType, StrType, ListType, BuiltinFunc, BaseStringType, ANY_TYPE


##  ReprFunc
##
class ReprFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'repr', StrType.get_object(),
                         [ANY_TYPE])
    return


##  RangeFunc
##
class RangeFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'range', ListType([IntType.get_object()]), 
                         [IntType],
                         [IntType, IntType])
    return


