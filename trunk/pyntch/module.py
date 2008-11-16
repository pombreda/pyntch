#!/usr/bin/env python
import sys
stderr = sys.stderr
from namespace import Namespace
from typenode import SimpleTypeNode, CompoundTypeNode
from construct import FuncType
from frame import ExceptionFrame


##  ModuleType
##
class ModuleType(FuncType, ExceptionFrame):
  
  ##  Attr
  ##
  class Attr(CompoundTypeNode):

    def __init__(self, name, module):
      CompoundTypeNode.__init__(self)
      self.name = name
      self.module = module
      return

    def __repr__(self):
      return '%r.@%s' % (self.module, self.name)

  def __init__(self, reporter, tree, parent_space, name):
    from expression import FunCall
    FuncType.__init__(self, reporter, self, parent_space,
                      name, (), (), False, False, tree.node)
    ExceptionFrame.__init__(self)
    self.attrs = {}
    FunCall(self, tree, self, ())
    return
  
  def __repr__(self):
    return '<Module %s>' % self.name

  def get_attr(self, name):
    if name not in self.attrs:
      attr = self.Attr(name, self)
      self.attrs[name] = attr
      try:
        self.space[name].connect(attr)
      except KeyError:
        pass
    else:
      attr = self.attrs[name]
    return attr
  
  def show(self, p):
    p('[%s]' % self.name)
    for (k,v) in sorted(self.space):
      p(' %s = %s' % (k, v.describe()))
    self.body.show(p)
    return
  

##  BuiltinModuleType
##
class BuiltinModuleType(ModuleType):

  def __init__(self, name):
    SimpleTypeNode.__init__(self)
    self.name = name
    self.attrs = {}
    return

  def get_attr(self, name):
    if name not in self.attrs:
      attr = ModuleType.Attr(name, self)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def __repr__(self):
    return '<BuiltinModule %s>' % self.name


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

    # int,float,bool,buffer,chr,dict,file,open,list,set,frozenset,
    # object,xrange,slice,type,unicode,tuple,super,str,staticmethod,classmethod,reversed
    self.register_var('int').bind(builtin_funcs.IntFunc())
    self.register_var('str').bind(builtin_funcs.StrFunc())

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


# find_module
class ModuleNotFound(Exception): pass

def find_module(name, paths, debug=0):
  import os.path
  if debug:
    print >>stderr, 'find_module: name=%r' % name
  fname = name+'.py'
  for dirname in paths:
    path = os.path.join(dirname, name)
    if os.path.exists(path):
      return path
    path = os.path.join(dirname, fname)
    if os.path.exists(path):
      return path
  raise ModuleNotFound(name)

# load_module
def load_module(modname, asname=None, paths=['.'], debug=0):
  from compiler import parseFile
  def rec(n):
    n._modname = modname
    for c in n.getChildNodes():
      rec(c)
    return
  path = find_module(modname, paths)
  name = asname or modname
  if debug:
    print >>stderr, 'load_module: %r' % path
  tree = parseFile(path)
  rec(tree)
  return ModuleType(None, tree, BUILTIN_NAMESPACE, name)

