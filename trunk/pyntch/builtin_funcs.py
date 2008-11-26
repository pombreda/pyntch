#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import SimpleTypeNode, CompoundTypeNode
from exception import ExceptionType, ExceptionRaiser
from function import ClassType, InstanceType
from builtin_types import NumberType, BoolType, IntType, LongType, StrType, ListType, BuiltinFunc, INT_ARG, STR_ARG, ANY_ARG


##  IntFunc
##
class IntFunc(BuiltinFunc):

  class IntConversion(CompoundTypeNode):
    
    def __init__(self, parent_frame, obj):
      CompoundTypeNode.__init__(self)
      self.parent_frame = parent_frame
      obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src.types:
        if isinstance(obj, BaseStringType):
          self.parent_frame.raise_expt(ExceptionType(
            'ValueError',
            'might be conversion error'))
        elif isinstance(obj, (NumberType, BoolType)):
          pass
        else:
          self.parent_frame.raise_expt(ExceptionType(
            'TypeError',
            'cannot convert: %s' % obj))
      return

  def accept_arg(self, caller, i):
    if i == 0:
      return self.IntConversion(caller, self.args[i])
    else:
      return BuiltinFunc.accept_arg(self, caller, i)

  def __init__(self):
    BuiltinFunc.__init__(self, 'int', IntType.get(),
                         [],
                         [ANY_ARG, INT_ARG])
    return


##  StrFunc
##
class StrFunc(BuiltinFunc):

  class StrConversion(CompoundTypeNode):
    
    def __init__(self, parent_frame):
      CompoundTypeNode.__init__(self)
      self.parent_frame = parent_frame
      return
    
    def recv(self, src):
      for obj in src.types:
        if isinstance(obj, InstanceType):
          ClassType.OptionalAttr(obj, '__str__').call(self, ())
      return

  def accept_arg(self, caller, _):
    return self.StrConversion(caller)

  def __init__(self):
    BuiltinFunc.__init__(self, 'str', StrType.get(),
                         [],
                         [ANY_ARG])
    return


##  RangeFunc
##
class RangeFunc(BuiltinFunc):

  def __init__(self):
    BuiltinFunc.__init__(self, 'range', ListType([IntType.get()]), 
                         [INT_ARG],
                         [INT_ARG, INT_ARG])
    return
