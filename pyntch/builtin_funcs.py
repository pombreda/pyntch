#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import SimpleTypeNode, CompoundTypeNode, NodeTypeError, BuiltinType
from exception import ExceptionRaiser, TypeChecker
from exception import TypeErrorType
from namespace import Namespace
from function import ClassType, InstanceType
from builtin_types import TypeType, NumberType, BoolType, IntType, LongType, FloatType, \
     BaseStringType, StrType, UnicodeType, ANY_TYPE, \
     InternalFunc, InternalConstFunc
from aggregate_types import ListObject, TupleObject, IterObject


##  BuiltinFunc
class BuiltinFunc(InternalFunc, BuiltinType):
  def __init__(self, name, args=None, optargs=None, expts=None):
    InternalFunc.__init__(self, name, args=args, optargs=optargs, expts=expts)
    BuiltinType.__init__(self)
    return
  def __repr__(self):
    return '<builtin %s>' % self.name
  @classmethod
  def get_name(self):
    return 'builtin'

##  BuiltinConstFunc
class BuiltinConstFunc(InternalConstFunc, BuiltinType):
  def __init__(self, name, retype, args=None, optargs=None, expts=None):
    InternalConstFunc.__init__(self, name, retype, args=args, optargs=optargs, expts=expts)
    BuiltinType.__init__(self)
    return
  def __repr__(self):
    return '<builtin %s>' % self.name
  @classmethod
  def get_name(self):
    return 'builtin'


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
    BuiltinConstFunc.__init__(self, 'range', ListObject([IntType.get_object()]), 
                              [IntType],
                              [IntType, IntType])
    return


##  CallableFunc
##
class CallableFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'callable', BoolType.get_object(), [ANY_TYPE])
    return


##  CmpFunc
##
class CmpFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'cmp', IntType.get_object(), [ANY_TYPE, ANY_TYPE])
    return


##  DirFunc
##
class DirFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'dir', ListObject([StrType.get_object()]), [], [ANY_TYPE])
    return


##  HashFunc
##
class HashFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'hash', IntType.get_object(), [ANY_TYPE])
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
    BuiltinConstFunc.__init__(self, 'id', IntType.get_object(), [ANY_TYPE])
    return


##  IsInstanceFunc
##
class IsInstanceFunc(BuiltinConstFunc):

  def __init__(self):
    BuiltinConstFunc.__init__(self, 'isinstance', BoolType.get_object(), [ANY_TYPE, TypeType])
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
      self.iterobj = IterObject([])
      CompoundTypeNode.__init__(self, [self.iterobj])
      obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src:
        try:
          obj.get_iter(self).connect(self.iterobj.elemall)
        except NodeTypeError:
          self.frame.raise_expt(TypeErrorType.occur('%r is not iterable: %r' % (src, obj)))
      return self.iterobj
  
  def process_args(self, frame, args, kwargs):
    return self.IterConversion(frame, args[0])

  def __init__(self):
    BuiltinFunc.__init__(self, 'iter', [ANY_TYPE])
    return