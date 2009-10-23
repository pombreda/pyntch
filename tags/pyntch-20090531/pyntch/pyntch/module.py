#!/usr/bin/env python
import sys, os.path, compiler
from pyntch.typenode import BuiltinType, BuiltinObject
from pyntch.frame import ExecutionFrame
from pyntch.namespace import Namespace


##  IndentedStream
##
class IndentedStream(object):
  
  def __init__(self, fp, width=2):
    self.fp = fp
    self.width = width
    self.i = 0
    return

  def write(self, s):
    self.fp.write(' '*(self.width*self.i)+s+'\n')
    return

  def indent(self, d):
    self.i += d
    return

  
##  TreeReporter
##
class TreeReporter(object):

  def __init__(self, parent=None, name=None):
    self.children = []
    if parent:
      parent.register(name, self)
    return

  def register(self, name, child):
    self.children.append((name, child))
    return

  def show(self, out):
    return

  def showrec(self, out):
    self.show(out)
    out.write('')
    out.indent(+1)
    for (name,reporter) in self.children:
      reporter.showrec(out)
    out.indent(-1)
    return
  
  
class ModuleNotFound(Exception):
  def __init__(self, name, path):
    self.name = name
    self.path = path
    return
  

##  Module
##
class ModuleObject(BuiltinObject):
  
  def __init__(self, name, space):
    self.name = name
    self.space = space
    BuiltinObject.__init__(self, ModuleType.get_typeobj())
    return
  
  def __repr__(self):
    return '<Module %s>' % (self.name,)

  def get_name(self):
    return self.name

  def get_attr(self, frame, anchor, name, write=False):
    from basic_types import StrType
    if name == '__file__':
      return StrType.get_object()
    return self.space.register_var(name)
  
  
class ModuleType(BuiltinType):
  
  TYPE_NAME = 'module'


##  Python Module
##
class PythonModuleObject(ModuleObject, TreeReporter):

  def __init__(self, name, parent_space, path=None):
    self.path = path
    self.frame = ExecutionFrame(None, None)
    ModuleObject.__init__(self, name, Namespace(parent_space, name))
    TreeReporter.__init__(self, None, name)
    return
  
  def __repr__(self):
    return '<Module %s (%s)>' % (self.name, self.path)

  def load(self, tree):
    from pyntch.syntax import build_stmt
    from pyntch.config import ErrorConfig
    from pyntch.exception import ImportErrorType
    evals = []
    try:
      self.space.register_names(tree)
      build_stmt(self, self.frame, self.space, tree, evals, isfuncdef=True)
    except ModuleNotFound, e:
      if ErrorConfig.ignore_module_notfound:
        pass
      else:
        self.frame.raise_expt(ImportErrorType.occur(e.name))
        print >>sys.stderr, 'module not found: %r' % e.name
    return

  def get_path(self):
    return self.path

  def show(self, out):
    out.write('[%s]' % self.name)
    blocks = set( name for (name,_) in self.children )
    for (name,v) in sorted(self.space):
      if name in blocks: continue
      out.write('  %s = %s' % (name, v.describe()))
    self.frame.show(out)
    return
  

##  Interpreter
##
class Interpreter(object):

  debug = 0
  
  module_path = None
  PATH2MODULE = None
  NAME2MODULE = None
  DEFAULT_NAMESPACE = None

  @classmethod
  def initialize(klass, module_path):
    # global parameters.
    from pyntch.namespace import BuiltinTypesNamespace, BuiltinExceptionsNamespace, BuiltinNamespace, DefaultNamespace
    klass.module_path = module_path
    default = DefaultNamespace()
    builtin = BuiltinNamespace(default)
    types = BuiltinTypesNamespace(builtin)
    exceptions = BuiltinExceptionsNamespace(builtin)
    builtin.import_all(types)
    builtin.import_all(exceptions)
    default.import_all(builtin)
    klass.DEFAULT_NAMESPACE = default
    klass.NAME2MODULE = {
      '__builtin__': ModuleObject('__builtin__', builtin),
      'types': ModuleObject('types', types),
      'exceptions': ModuleObject('exceptions', exceptions),
      }
    klass.PATH2MODULE = {}
    return

  # find_module(name)
  #   return the full path for a given module name.
  @classmethod
  def find_module(klass, name, modpath):
    if klass.debug:
      print >>sys.stderr, 'find_module: name=%r' % name, modpath
    for dirname in modpath:
      for fname in (name+'.pyi', name+'.py'):
        path = os.path.join(dirname, fname)
        if os.path.isfile(path):
          return path
      path = os.path.join(dirname, name)
      if os.path.isdir(path):
        path = os.path.join(path, '__init__.py')
        if os.path.isfile(path):
          return path
    raise ModuleNotFound(name, modpath)

  # load_file
  @classmethod
  def load_file(klass, path, modname):
    path = os.path.normpath(path)
    if path in klass.PATH2MODULE:
      module = klass.PATH2MODULE[path]
    else:
      print >>sys.stderr, 'loading: %r' % path
      dirname = os.path.dirname(path)
      if dirname not in klass.module_path:
        klass.module_path.insert(0, dirname)
      module = PythonModuleObject(modname, klass.DEFAULT_NAMESPACE, path)
      klass.PATH2MODULE[path] = module
      klass.NAME2MODULE[modname] = module
      try:
        tree = compiler.parseFile(path)
      except IOError:
        raise ModuleNotFound(modname, path)
      def rec(n):
        n._module = module
        for c in n.getChildNodes():
          rec(c)
        return
      rec(tree)
      module.load(tree)
    return module

  # load_module
  @classmethod
  def load_module(klass, fullname):
    if klass.debug:
      print >>sys.stderr, 'load_module: %r...' % fullname
    if fullname in klass.NAME2MODULE:
      module = klass.NAME2MODULE[fullname]
    else:
      modpath = klass.module_path
      modname = fullname
      try:
        path = klass.find_module(modname, modpath)
      except ModuleNotFound, e:
        try:
          i = fullname.rindex('.')
          parent = klass.load_module(fullname[:i])
          modpath = [ os.path.dirname(parent.path) ]
          modname = fullname[i+1:]
        except ValueError:
          raise e
      path = klass.find_module(modname, modpath)
      module = klass.load_file(path, fullname)
    return module