#!/usr/bin/env python

##  This module should not be imported as toplevel,
##  as it causes circular imports!

from typenode import SimpleTypeNode, CompoundTypeNode
from exception import ExceptionType, ExceptionRaiser
from namespace import Namespace
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


##  BuiltinNamespace
##
class BuiltinNamespace(Namespace):

  def __init__(self):
    import builtin_types
    import builtin_funcs
    Namespace.__init__(self, None, '')
    self.register_var('True').bind(builtin_types.BoolType.get())
    self.register_var('False').bind(builtin_types.BoolType.get())
    self.register_var('None').bind(builtin_types.NoneType.get())
    self.register_var('__name__').bind(builtin_types.StrType.get())

    # int,long,float,bool,chr,dict,file,open,list,set,frozenset,
    # object,xrange,type,unicode,tuple,str,staticmethod,classmethod,reversed
    self.register_var('int').bind(builtin_funcs.IntFunc())
    #self.register_var('long').bind(builtin_funcs.LongFunc())
    #self.register_var('float').bind(builtin_funcs.FloatFunc())
    #self.register_var('bool').bind(builtin_funcs.BoolFunc())
    #self.register_var('chr').bind(builtin_funcs.ChrFunc())
    #self.register_var('dict').bind(builtin_funcs.DictFunc())
    #self.register_var('file').bind(builtin_funcs.FileFunc())
    #self.register_var('open').bind(builtin_funcs.FileFunc())
    #self.register_var('list').bind(builtin_funcs.ListFunc())
    self.register_var('str').bind(builtin_funcs.StrFunc())
    #self.register_var('unicode').bind(builtin_funcs.UnicodeFunc())
    #self.register_var('set').bind(builtin_funcs.SetFunc())
    #self.register_var('tuple').bind(builtin_funcs.TupleFunc())
    #self.register_var('object').bind(builtin_funcs.ObjectFunc())
    #self.register_var('xrange').bind(builtin_funcs.XRangeFunc())
    #self.register_var('type').bind(builtin_funcs.TypeFunc())
    #self.register_var('staticmethod').bind(builtin_funcs.StaticMethodFunc())
    #self.register_var('classmethod').bind(builtin_funcs.ClassMethodFunc())
    #self.register_var('reversed').bind(builtin_funcs.ReversedFunc())

    # abs,all,any,apply,basestring,callable,chr,
    # cmp,coerce,compile,complex,delattr,dir,divmod,enumerate,eval,
    # execfile,filter,getattr,globals,hasattr,hash,
    # hex,id,input,intern,isinstance,issubclass,iter,len,locals,
    # long,map,max,min,oct,ord,pow,property,range,raw_input,
    # reduce,reload,repr,round,setattr,sorted,
    # sum,unichr,vars,xrange,zip
    self.register_var('range').bind(builtin_funcs.RangeFunc())
    
    return


##  Global stuff
##
BUILTIN_NAMESPACE = BuiltinNamespace()
