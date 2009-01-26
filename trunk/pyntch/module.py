#!/usr/bin/env python
import sys, os.path
stderr = sys.stderr
from typenode import TreeReporter, BuiltinType
from exception import ExceptionFrame
from namespace import Namespace


##  ModuleType
##
class ModuleType(BuiltinType):
  
  def __init__(self, name, space):
    self.name = name
    self.space = space
    BuiltinType.__init__(self)
    return
  
  def __repr__(self):
    return '<Module %s>' % (self.name,)

  @classmethod
  def get_name(klass):
    return 'module'

  def get_attr(self, name, write=False):
    return self.space.register_var(name)


##  PythonModuleType
##
class PythonModuleType(ModuleType, TreeReporter, ExceptionFrame):

  def __init__(self, name, parent_space, path=None):
    self.path = path
    ModuleType.__init__(self, name, Namespace(parent_space, name))
    TreeReporter.__init__(self, None, name)
    ExceptionFrame.__init__(self)
    return
  
  def __repr__(self):
    return '<Module %s (%s)>' % (self.name, self.path)

  def load(self, tree):
    from syntax import build_stmt
    evals = []
    self.space.register_names(tree)
    build_stmt(self, self, self.space, tree, evals, isfuncdef=True)
    return

  def show(self, p):
    p('[%s]' % self.name)
    blocks = set( name for (name,_) in self.children )
    for (name,v) in sorted(self.space):
      if name in blocks: continue
      p('  %s = %s' % (name, v.describe()))
    for expt in self.expt:
      p('  raises %r' % expt)
    return
  

##  Interpreter
##
class Interpreter(object):

  class ModuleNotFound(Exception): pass
  
  debug = 0
  
  module_path = None
  MODULE_CACHE = None
  DEFAULT_NAMESPACE = None

  @classmethod
  def initialize(klass, module_path):
    # global parameters.
    from namespace import BuiltinTypesNamespace, BuiltinExceptionsNamespace, BuiltinNamespace, DefaultNamespace
    klass.module_path = module_path
    default = DefaultNamespace()
    builtin = BuiltinNamespace(default)
    types = BuiltinTypesNamespace(builtin)
    exceptions = BuiltinExceptionsNamespace(builtin)
    builtin.import_all(types)
    builtin.import_all(exceptions)
    default.import_all(builtin)
    klass.DEFAULT_NAMESPACE = default
    klass.MODULE_CACHE = {
      '__builtin__': ModuleType('__builtin__', builtin),
      'types': ModuleType('types', types),
      'exceptions': ModuleType('exceptions', exceptions),
      }
    return

  # find_module(name)
  #   return the full path for a given module name.
  @classmethod
  def find_module(klass, name, modpath):
    if klass.debug:
      print >>stderr, 'find_module: name=%r' % name, modpath
    for dirname in modpath:
      for fname in (name+'.py', name+'.pyi'):
        path = os.path.join(dirname, fname)
        if os.path.isfile(path):
          return path
      path = os.path.join(dirname, name)
      if os.path.isdir(path):
        path = os.path.join(path, '__init__.py')
        if os.path.isfile(path):
          return path
    raise klass.ModuleNotFound(name, modpath)

  # load_file
  @classmethod
  def load_file(klass, path, modname):
    from compiler import parseFile
    if klass.debug:
      print >>stderr, 'load_file: %r' % path
    def rec(n):
      n._modname = modname
      for c in n.getChildNodes():
        rec(c)
      return
    dirname = os.path.dirname(path)
    if dirname not in klass.module_path:
      klass.module_path.insert(0, dirname)
    module = PythonModuleType(modname, klass.DEFAULT_NAMESPACE, path)
    klass.MODULE_CACHE[modname] = module
    try:
      tree = parseFile(path)
    except IOError:
      raise klass.ModuleNotFound(modname)
    rec(tree)
    module.load(tree)
    return module

  # load_module
  @classmethod
  def load_module(klass, fullname):
    if klass.debug:
      print >>stderr, 'load_module: %r...' % fullname
    if fullname in klass.MODULE_CACHE:
      module = klass.MODULE_CACHE[fullname]
    else:
      try:
        i = fullname.rindex('.')
        parent = klass.load_module(fullname[:i])
        modpath = [ os.path.dirname(parent.path) ]
        name = fullname[i+1:]
      except ValueError:
        modpath = klass.module_path
        name = fullname
      path = klass.find_module(name, modpath)
      module = klass.load_file(path, fullname)
    return module
