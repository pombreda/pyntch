#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import SimpleTypeNode, CompoundTypeNode
from frame import ExceptionType, ExceptionRaiser
from construct import ClassType, InstanceType
from builtin_types import IntType, StrType, BuiltinFuncType


##  IntFunc
##
class IntFunc(BuiltinFuncType):

  NAME = 'int'

  ##  Body
  ##
  class Body(BuiltinFuncType.Body):
    
    def __init__(self, parent_frame, obj, base=None):
      BuiltinFuncType.Body.__init__(self, parent_frame)
      obj.connect(self)
      if base:
        base.connect(self, self.recv_xint)
      return
  
    def recv(self, src):
      for obj in src.types:
        if not isinstance(obj, BuiltinType):
          self.raise_expt(ExceptionType(
            'TypeError',
            'unsupported conversion: %s' % obj.typename))
          continue
        if obj.typename in ('int','long','float','bool'):
          continue
        if obj.typename in ('str','unicode','basestring'):
          self.raise_expt(ExceptionType(
            'ValueError',
            'might be conversion error'))
          continue
        if obj.typename in ('complex',):
          self.raise_expt(ExceptionType(
            'TypeError',
            'cannot convert complex'))
          continue
      return

  def call(self, caller, args):
    if not args:
      return IntType.get()
    if 2 < len(args):
      caller.raise_expt(ExceptionType(
        'TypeError',
        'too many argument: more than 2'))
    return self.Body(caller, *args)


##  StrFunc
##
class StrFunc(BuiltinFuncType):

  NAME = 'str'

  ##  Body
  ##
  class Body(BuiltinFuncType.Body):
    
    def __init__(self, parent_frame, obj):
      BuiltinFuncType.Body.__init__(self, parent_frame)
      self.types.add(StrType.get())
      self.obj = obj
      self.obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src.types:
        if isinstance(obj, InstanceType):
          ClassType.OptionalAttr(obj, '__str__').call(self, ())
      return

  def call(self, caller, args):
    if not args:
      return StrType.get()
    if 1 < len(args):
      caller.raise_expt(ExceptionType(
        'TypeError',
        'too many argument: more than 1'))
    return self.Body(caller, *args)


##  RangeFunc
##
class RangeFunc(BuiltinFuncType):

  NAME = 'range'
  
  ##  Body
  ##
  class Body(BuiltinFuncType.Body):
    
    def __init__(self, parent_frame, loc, args):
      BuiltinFuncType.Body.__init__(self, parent_frame, loc)
      for arg in args:
        arg.connect(self, self.recv_int)
      XXX
      self.ListType([IntType.get()])
      return
  
  def call(self, caller, args):
    if not args or 3 < len(args):
      caller.raise_expt(ExceptionType(
        'TypeError',
        'invalid number of args: %d' % len(args)))
    return self.Body(caller, args)

  
