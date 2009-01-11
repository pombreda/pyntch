#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import SimpleTypeNode, CompoundTypeNode
from exception import ExceptionType, ExceptionRaiser, TypeChecker
from namespace import Namespace
from function import ClassType, InstanceType
from builtin_types import NumberType, BoolType, IntType, LongType, StrType, ListType, BuiltinFunc, BaseStringType, ANY_TYPE


##  IntFunc
##
# class IntFunc(BuiltinFunc):

#   class IntConversion(CompoundTypeNode):
    
#     def __init__(self, parent_frame, obj):
#       CompoundTypeNode.__init__(self)
#       self.parent_frame = parent_frame
#       obj.connect(self)
#       return
    
#     def recv(self, src):
#       for obj in src.types:
#         if isinstance(obj, BaseStringType):
#           self.parent_frame.raise_expt(ExceptionType(
#             'ValueError',
#             'might be conversion error'))
#         elif isinstance(obj, (NumberType, BoolType)):
#           pass
#         else:
#           self.parent_frame.raise_expt(ExceptionType(
#             'TypeError',
#             'cannot convert: %s' % obj))
#       return

#   def accept_arg(self, caller, i):
#     if i == 0:
#       return self.IntConversion(caller, self.args[i])
#     else:
#       return BuiltinFunc.accept_arg(self, caller, i)

#   def __init__(self):
#     BuiltinFunc.__init__(self, 'int', IntType.get_object(),
#                          [],
#                          [ANY_TYPE, IntType])
#     return


##  StrFunc
##
# class StrFunc(BuiltinFunc):

#   class StrConversion(CompoundTypeNode, ExceptionRaiser):
    
#     def __init__(self, parent_frame):
#       CompoundTypeNode.__init__(self)
#       ExceptionRaiser.__init__(self, parent_frame)
#       return
    
#     def recv(self, src):
#       for obj in src.types:
#         if isinstance(obj, InstanceType):
#           value = ClassType.OptionalAttr(obj, '__str__').call(self, ())
#           value.connect(TypeChecker(self, BaseStringType, 'the return value of __str__ method'))
#           value = ClassType.OptionalAttr(obj, '__repr__').call(self, ())
#           value.connect(TypeChecker(self, BaseStringType, 'the return value of __repr__ method'))
#       return

#   def accept_arg(self, caller, _):
#     return self.StrConversion(caller)

#   def __init__(self):
#     BuiltinFunc.__init__(self, 'str', StrType.get_object(),
#                          [],
#                          [ANY_TYPE])
#     return


##  RangeFunc
##
class RangeFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'range', ListType([IntType.get_object()]), 
                         [IntType],
                         [IntType, IntType])
    return


