#!/usr/bin/env python
import sys, os.path, compiler
from pyntch.typenode import BuiltinType, BuiltinObject, NodeAssignError
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
  
  
##  Module
##
class ModuleNotFound(Exception):
  
  def __init__(self, name, path=None):
    self.name = name
    self.path = path
    return
  
class ModuleObject(BuiltinObject):
  
  def __init__(self, name, space, level=0):
    self.name = name
    self.space = space
    self.level = level
    BuiltinObject.__init__(self, ModuleType.get_typeobj())
    return
  
  def __repr__(self):
    return '<Module %s>' % (self.name,)

  def get_path(self):
    return '?'

  def get_name(self):
    return self.name

  def get_attr(self, frame, anchor, name, write=False):
    from pyntch.basic_types import StrType
    if name == '__file__':
      if write: raise NodeAssignError(name)
      return StrType.get_object()
    return self.space.register_var(name)

  def add_child(self, name, module):
    self.space.register_var(name).bind(module)
    return

  def load_module(self, name):
    raise ModuleNotFound(name)
  
  def import_object(self, name):
    if name in self.space:
      return self.space[name]
    raise ModuleNotFound(name)
  
class ModuleType(BuiltinType):
  
  TYPE_NAME = 'module'


##  Python Module
##
class PythonModuleObject(ModuleObject, TreeReporter):

  def __init__(self, name, parent_space, path, modpath, level=0):
    self.path = path
    self.modpath = modpath + [os.path.dirname(self.path)]
    self.frame = ExecutionFrame(None, None)
    ModuleObject.__init__(self, name, Namespace(parent_space, name), level=level)
    TreeReporter.__init__(self, None, name)
    return
  
  def __repr__(self):
    return '<Module %s (%s)>' % (self.name, self.path)

  def set(self, tree):
    from pyntch.syntax import build_stmt
    from pyntch.config import ErrorConfig
    from pyntch.exception import ImportErrorType
    self.space.register_names(tree)
    build_stmt(self, self.frame, self.space, tree, [], isfuncdef=True)
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

  def load_module(self, name):
    if self.name == 'os' and name == 'path':
      # os.path hack
      return Interpreter.load_module('posixpath', [], level=self.level+1)
    else:
      return Interpreter.load_module(name, self.modpath, level=self.level+1)

  def import_object(self, name):
    if name in self.space:
      return self.space[name]
    return self.load_module(name)[-1]
  

##  Interpreter
##
class Interpreter(object):

  verbose = 0
  debug = 0
  lines = 0
  files = 0
  
  stub_path = None
  PATH2MODULE = None
  BUILTIN_MODULE = None
  DEFAULT_NAMESPACE = None

  @classmethod
  def initialize(klass, stub_path):
    # global parameters.
    from pyntch.namespace import BuiltinTypesNamespace, BuiltinExceptionsNamespace, BuiltinNamespace, DefaultNamespace
    klass.stub_path = stub_path
    default = DefaultNamespace()
    builtin = BuiltinNamespace(default)
    types = BuiltinTypesNamespace(builtin)
    exceptions = BuiltinExceptionsNamespace(builtin)
    builtin.import_all(types)
    builtin.import_all(exceptions)
    default.import_all(builtin)
    klass.DEFAULT_NAMESPACE = default
    klass.BUILTIN_MODULE = {
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
    modpath = klass.stub_path + modpath
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
  def load_file(klass, modname, path, modpath, level=0):
    path = os.path.normpath(path)
    if path in klass.PATH2MODULE:
      module = klass.PATH2MODULE[path]
    else:
      if klass.verbose:
        print >>sys.stderr, ' '*level+'loading: %r as %r' % (path, modname)
      module = PythonModuleObject(modname, klass.DEFAULT_NAMESPACE, path, modpath, level=level)
      klass.PATH2MODULE[path] = module
      try:
        fp = file(path)
        for _ in fp:
          klass.lines += 1
        fp.close()
        klass.files += 1
        tree = compiler.parseFile(path)
      except IOError:
        raise ModuleNotFound(modname, path)
      def rec(n):
        n._module = module
        for c in n.getChildNodes():
          rec(c)
        return
      rec(tree)
      module.set(tree)
    return module

  # load_module
  @classmethod
  def load_module(klass, fullname, modpath, level=0):
    if klass.debug:
      print >>sys.stderr, 'load_module: %r...' % fullname
    if fullname in klass.BUILTIN_MODULE:
      return [klass.BUILTIN_MODULE[fullname]]
    modules = []
    module = None
    for name in fullname.split('.'):
      if module:
        module = module.load_module(name)[-1]
      else:
        try:
          path = klass.find_module(name, modpath)
          module = klass.load_file(name, path, modpath, level=level)
        except ModuleNotFound:
          if klass.verbose:
            print >>sys.stderr, ' '*level+'not found: %r' % name
          raise
      modules.append(module)
    return modules
