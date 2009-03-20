#!/usr/bin/env python

from typenode import CompoundTypeNode, \
     NodeTypeError, NodeAttrError, BuiltinType, BuiltinObject, UndefinedTypeNode
from namespace import Namespace
from module import TreeReporter
from frame import ExecutionFrame


##  BoundMethodType
##
class BoundMethodType(BuiltinType):

  TYPE_NAME = 'boundmethod'

  def __init__(self, arg0, func):
    self.arg0 = arg0
    self.func = func
    BuiltinType.__init__(self)
    return

  def __repr__(self):
    return '<boundmethod %r(%s=%r)>' % (self.func, self.func.argnames[0], self.arg0)
  
  def get_type(self):
    return self

  def call(self, frame, args, kwargs):
    return self.func.call(frame, (self.arg0,)+tuple(args), kwargs)


##  ClassType
##
class ClassType(BuiltinType, TreeReporter):

  TYPE_NAME = 'class'
  
  ##  ClassAttr
  ##
  class ClassAttr(CompoundTypeNode):

    def __init__(self, name, klass, baseklass=None):
      self.name = name
      self.klass = klass
      self.done = set()
      CompoundTypeNode.__init__(self)
      if baseklass:
        baseklass.connect(self.recv_baseklass)
      return

    def __repr__(self):
      return '%r.%s' % (self.klass, self.name)

    def recv_baseklass(self, src):
      for klass in src:
        if klass in self.done: continue
        self.done.add(klass)
        try:
          klass.get_attr(self.name).connect(self.recv)
        except NodeAttrError:
          pass
      return

    def check_undefined(self):
      return

  def __init__(self, name, bases):
    self.name = name
    self.bases = bases
    self.attrs = {}
    self.boundmethods = {}
    self.baseklass = CompoundTypeNode(bases)
    self.frames = set()
    BuiltinType.__init__(self)
    self.instance = InstanceObject(self)
    return

  def __repr__(self):
    return ('<class %s>' % self.fullname())
  
  def get_name(self):
    return self.fullname()
  
  def is_subclass(self, klassobj):
    if self is klassobj: return True
    for klass in self.baseklass:
      if isinstance(klass, ClassType):
        if klass.is_subclass(klassobj): return True
    return False

  def get_attr(self, name, write=False):
    if name not in self.attrs:
      attr = self.ClassAttr(name, self, self.baseklass)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def bind_func(self, func):
    if func not in self.boundmethods:
      method = BoundMethodType(self, func)
      self.boundmethods[func] = method
    else:
      method = self.boundmethods[func]
    return method

  def call(self, frame, args, kwargs):
    from expression import MethodCall
    assert isinstance(frame, ExecutionFrame)
    self.frames.add(frame)
    MethodCall(frame, self, '__init__', (self.instance,)+args, kwargs)
    return self.instance
  
class PythonClassType(ClassType, TreeReporter):
  
  def __init__(self, parent_reporter, parent_frame, parent_space, name, bases, code, evals, tree):
    TreeReporter.__init__(self, parent_reporter, name)
    ClassType.__init__(self, name, bases)
    from syntax import build_stmt
    self.loc = (tree._module, tree.lineno)
    self.space = Namespace(parent_space, name)
    if code:
      self.space.register_names(code)
      build_stmt(self, parent_frame, self.space, code, evals)
    for (name,var) in self.space:
      # Do not consider the values of attributes inherited from the base class
      # if they are explicitly overriden.
      attr = self.ClassAttr(name, self)
      var.connect(attr.recv)
      self.attrs[name] = attr
    return

  def fullname(self):
    return self.space.fullname()
  
  def show(self, out):
    (module,lineno) = self.loc
    out.write('### %s(%s)' % (module.get_path(), lineno))
    for frame in self.frames:
      (module,lineno) = frame.getloc()
      out.write('# instantiated at %s(%d)' % (module.get_path(), lineno))
    if self.bases:
      out.write('class %s(%s):' % (self.name, ', '.join( base.fullname() for base in self.baseklass.types )))
    else:
      out.write('class %s:' % self.name)
    blocks = set( name for (name,_) in self.children )
    for (name, attr) in sorted(self.attrs.iteritems()):
      if name in blocks or not attr.types: continue
      out.write('  class.%s = %s' % (name, attr.describe()))
    for (name, attr) in sorted(self.instance.attrs.iteritems()):
      if name in blocks or not attr.types: continue
      out.write('  instance.%s = %s' % (name, attr.describe()))
    return


##  InstanceType
##
class InstanceObject(BuiltinObject):

  TYPE_NAME = 'instance'
  
  ##  InstanceAttr
  ##
  class InstanceAttr(ClassType.ClassAttr):

    def __init__(self, name, instance):
      self.instance = instance
      self.processed = set()
      ClassType.ClassAttr.__init__(self, name, instance.klass, instance.klass.baseklass)
      instance.klass.connect(self.recv_baseklass)
      return

    def __repr__(self):
      return '%r.%s' % (self.instance, self.name)

    def recv(self, src):
      from function import FuncType
      from basic_types import StaticMethodObject, ClassMethodObject
      for obj in src:
        if obj in self.processed: continue
        self.processed.add(obj)
        if isinstance(obj, StaticMethodObject):
          obj = obj.get_object()
        elif isinstance(obj, ClassMethodObject):
          obj = self.klass.bind_func(obj.get_object())
        elif isinstance(obj, FuncType):
          obj = self.instance.bind_func(obj)
        self.update_type(obj)
      return

  #
  def __init__(self, klass):
    self.klass = klass
    self.attrs = {}
    self.boundmethods = {}
    BuiltinObject.__init__(self, klass)
    for (name, value) in klass.attrs.iteritems():
      value.connect(self.get_attr(name).recv)
    return
  
  def __repr__(self):
    return ('<instance %s>' % self.klass.fullname())
  
  def get_type(self):
    return self.klass

  def is_type(self, *typeobjs):
    for typeobj in typeobjs:
      if self.klass.is_subclass(typeobj): return True
    return False

  def get_attr(self, name, write=False):
    if name not in self.attrs:
      attr = self.InstanceAttr(name, self)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def get_iter(self, frame):
    from expression import MethodCall
    assert isinstance(frame, ExecutionFrame)
    return MethodCall(frame, self, '__iter__')

  def get_reversed(self, frame):
    from expression import MethodCall
    assert isinstance(frame, ExecutionFrame)
    return MethodCall(frame, self, '__reversed__')

  def get_element(self, frame, sub, write=False):
    from expression import MethodCall
    if write:
      return MethodCall(frame, self, '__setelem__', sub)
    else:
      return MethodCall(frame, self, '__getelem__', sub)
    
  def get_slice(self, frame, subs, write=False):
    from expression import MethodCall
    if write:
      return MethodCall(frame, self, '__setslice__', sub)
    else:
      return MethodCall(frame, self, '__getslice__', sub)
  
  def bind_func(self, func):
    if func not in self.boundmethods:
      method = BoundMethodType(self, func)
      self.boundmethods[func] = method
    else:
      method = self.boundmethods[func]
    return method

class InstanceType(BuiltinType):
  TYPE_NAME = 'object'
