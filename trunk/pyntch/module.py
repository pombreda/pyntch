#!/usr/bin/env python
import sys, os.path
stderr = sys.stderr
from typenode import SimpleTypeNode, CompoundTypeNode
from function import TreeReporter
from exception import ExceptionFrame
from namespace import Namespace


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
    SimpleTypeNode.__init__(self)
    TreeReporter.__init__(self, parent_reporter)
    ExceptionFrame.__init__(self)
    return
  
  def __repr__(self):
    return '<Module %s (%s)>' % (self.name, self.path)

  def raise_expt(self, expt):
    print expt
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
    for (k,v) in sorted(self.space):
      p('  %s = %s' % (k, v.describe()))
    #self.body.show(p)
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
  from builtin_funcs import BUILTIN_NAMESPACE
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
    module = ModuleType(None, BUILTIN_NAMESPACE, fullname, path)
    MODULE_CACHE[fullname] = module
    if debug:
      print >>stderr, 'found_module: %r' % module
    tree = parseFile(path)
    rec(tree)
    module.load(tree)
  return module
