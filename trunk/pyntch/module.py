#!/usr/bin/env python
import sys, os.path
stderr = sys.stderr
from typenode import TreeReporter, SimpleTypeNode, CompoundTypeNode
from exception import ExceptionFrame
from namespace import Namespace
import builtin_types
import aggregate_types
import builtin_funcs


##  BuiltinNamespace
##
class BuiltinNamespace(Namespace):

  def __init__(self):
    self.parent_space = None
    self.name = '(global)'
    self.vars = {}
    self.msgs = []
    self.global_space = self
    #
    self.register_var('True').bind(builtin_types.BoolType.get_object())
    self.register_var('False').bind(builtin_types.BoolType.get_object())
    self.register_var('None').bind(builtin_types.NoneType.get_object())
    self.register_var('__name__').bind(builtin_types.StrType.get_object())
    self.register_var('__file__').bind(builtin_types.StrType.get_object())

    self.register_var('int').bind(builtin_types.IntType.get_type())
    self.register_var('long').bind(builtin_types.LongType.get_type())
    self.register_var('float').bind(builtin_types.FloatType.get_type())
    self.register_var('complex').bind(builtin_types.ComplexType.get_type())
    self.register_var('bool').bind(builtin_types.BoolType.get_type())
    self.register_var('basestring').bind(builtin_types.BaseStringType.get_type())
    self.register_var('str').bind(builtin_types.StrType.get_type())
    self.register_var('unicode').bind(builtin_types.UnicodeType.get_type())
    self.register_var('object').bind(builtin_types.ObjectType.get_type())
    self.register_var('file').bind(builtin_types.FileType.get_type())
    self.register_var('open').bind(builtin_types.FileType.get_type())
    self.register_var('list').bind(aggregate_types.ListType.get_type())
    self.register_var('tuple').bind(aggregate_types.TupleType.get_type())
    self.register_var('dict').bind(aggregate_types.DictType.get_type())
    self.register_var('set').bind(aggregate_types.SetType.get_type())
    
    #self.register_var('xrange').bind(builtin_types.XRangeFunc())
    #self.register_var('type').bind(builtin_types.TypeFunc())
    #self.register_var('staticmethod').bind(builtin_types.StaticMethodFunc())
    #self.register_var('classmethod').bind(builtin_types.ClassMethodFunc())
    #self.register_var('reversed').bind(builtin_types.ReversedFunc())
    #self.register_var('frozenset').bind(builtin_types.FrozenSetType())

    # abs,all,any,apply,callable,
    # cmp,dir,divmod,enumerate,
    # filter,hasattr,hash,
    # hex,id,isinstance,issubclass,
    # map,max,min,oct,ord,pow,property,raw_input,
    # reduce,round,sorted,sum,zip
    self.register_var('repr').bind(builtin_funcs.ReprFunc())
    self.register_var('len').bind(builtin_funcs.LenFunc())
    self.register_var('iter').bind(builtin_funcs.IterFunc())
    self.register_var('range').bind(builtin_funcs.RangeFunc())
    self.register_var('chr').bind(builtin_funcs.ChrFunc())
    self.register_var('unichr').bind(builtin_funcs.UnichrFunc())

    # buffer, coerce, intern
    # vars,eval,locals,globals,compile,getattr,setattr,delattr,reload,__import__,execfile,input
    return

  def fullname(self):
    return ''
  

##  Global stuff
##
BUILTIN_NAMESPACE = BuiltinNamespace()


##  ModuleType
##
class ModuleType(SimpleTypeNode, TreeReporter, ExceptionFrame):

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

  def __init__(self, parent_reporter, parent_space, name, path):
    self.name = name
    self.path = path
    self.attrs = {}
    self.space = Namespace(parent_space, name)
    SimpleTypeNode.__init__(self, self)
    TreeReporter.__init__(self, parent_reporter, name)
    ExceptionFrame.__init__(self)
    return
  
  def __repr__(self):
    return '<Module %s (%s)>' % (self.name, self.path)

  def raise_expt(self, expt):
    self.add_expt(expt)
    return
  
  def load(self, tree):
    from syntax import build_stmt
    evals = []
    self.space.register_names(tree)
    build_stmt(self, self, self.space, tree, evals, isfuncdef=True)
    return

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
    blocks = set( name for (name,_) in self.children )
    for (name,v) in sorted(self.space):
      if name in blocks: continue
      p('  %s = %s' % (name, v.describe()))
    for expt in self.expts:
      p('  raises %r' % expt)
    return
  

MODULE_CACHE = {}

class ModuleNotFound(Exception): pass
# find_module(name, modpath, debug=0)
#   return the full path for a given module name.
def find_module(name, modpath, debug=0):
  if debug:
    print >>stderr, 'find_module: name=%r' % name, modpath
  for dirname in ['stub']+modpath:
    for fname in (name+'.py', name+'.pyi'):
      path = os.path.join(dirname, fname)
      if os.path.isfile(path):
        return path
    path = os.path.join(dirname, name)
    if os.path.isdir(path):
      path = os.path.join(path, '__init__.py')
      if os.path.isfile(path):
        return path
  raise ModuleNotFound(name)

# load_module
def load_module(fullname, modpath=['.'], debug=0):
  from compiler import parseFile
  def rec(n):
    n._modname = fullname
    for c in n.getChildNodes():
      rec(c)
    return
  if debug:
    print >>stderr, 'load_module: %r...' % fullname
  if fullname in MODULE_CACHE:
    module = MODULE_CACHE[fullname]
  else:
    try:
      i = fullname.rindex('.')
      parent = load_module(fullname[:i], modpath=modpath, debug=debug)
      modpath = [ os.path.dirname(parent.path) ]
      name = fullname[i+1:]
    except ValueError:
      name = fullname
    path = find_module(name, modpath, debug=debug)
    fullname = fullname.replace('/','.')
    module = ModuleType(None, BUILTIN_NAMESPACE, fullname, path)
    MODULE_CACHE[fullname] = module
    if debug:
      print >>stderr, 'found_module: %r' % module
    tree = parseFile(path)
    rec(tree)
    module.load(tree)
  return module
