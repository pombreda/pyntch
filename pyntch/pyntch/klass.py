#!/usr/bin/env python

from typenode import TreeReporter, SimpleTypeNode, CompoundTypeNode, \
     NodeTypeError, NodeAttrError, BuiltinType, BuiltinObject
from namespace import Namespace
from frame import MustBeDefinedNode


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
  class ClassAttr(MustBeDefinedNode):

    def __init__(self, name, klass, baseklass=None):
      self.name = name
      self.klass = klass
      self.called = False
      self.args = []
      self.kwargs = {}
      self.done = set()
      self.retval = CompoundTypeNode()
      MustBeDefinedNode.__init__(self)
      if baseklass:
        baseklass.connect(self, self.recv_baseklass)
      return

    def __repr__(self):
      return '%r.%s' % (self.klass, self.name)

    def recv_baseklass(self, src):
      for klass in src:
        if klass in self.done: continue
        self.done.add(klass)
        try:
          klass.get_attr(self.name).connect(self)
        except NodeAttrError:
          pass
      return

    def optcall(self, frame, args, kwargs):
      # Remember the keyword arguments.
      for (kwname,kwvalue) in kwargs.iteritems():
        if kwname not in self.kwargs:
          var = CompoundTypeNode()
          self.kwargs[kwname] = var
        else:
          var = self.kwargs[kwname]
        kwvalue.connect(var)
      # Remember other arguments.
      while len(self.args) < len(args):
        self.args.append(CompoundTypeNode())
      for (var1,arg1) in zip(self.args, args):
        arg1.connect(var1)
      # Propagate the exceptions.
      self.connect_expt(frame)
      self.called = True
      self.update_calls()
      return self.retval
    
    def recv(self, src):
      CompoundTypeNode.recv(self, src)
      self.update_calls()
      return

    def update_calls(self):
      if not self.called: return
      for obj in self.types:
        try:
          obj.call(self, self.args, self.kwargs).connect(self.retval)
        except NodeTypeError:
          pass
        self.update_type(obj)
      return

    def check_undefined(self):
      return

  def __init__(self, name, bases):
    self.name = name
    self.bases = bases
    self.attrs = {}
    self.boundmethods = {}
    self.baseklass = CompoundTypeNode()
    self.frames = set()
    BuiltinType.__init__(self)
    self.instance = InstanceObject(self)
    for base in bases:
      base.connect(self.baseklass)
    return

  def __repr__(self):
    return ('<class %s>' % self.fullname())
  
  def get_type(self):
    return self

  def is_subclass(self, klassobj):
    if self is klassobj:
      return True
    else:
      for klass in self.baseklass:
        if isinstance(klass, ClassType):
          if klass.is_subclass(klassobj):
            return True
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
    self.frames.add(frame)
    self.get_attr('__init__').optcall(frame, (self.instance,)+args, kwargs)
    return self.instance
  
class PythonClassType(ClassType, TreeReporter):
  
  def __init__(self, parent_reporter, parent_frame, parent_space, name, bases, code, evals, loc):
    TreeReporter.__init__(self, parent_reporter, name)
    ClassType.__init__(self, name, bases)
    from syntax import build_stmt
    self.loc = loc
    self.space = Namespace(parent_space, name)
    if code:
      self.space.register_names(code)
      build_stmt(self, parent_frame, self.space, code, evals)
    for (name,var) in self.space:
      # Do not inherit attributes from the base class
      # if they are explicitly overriden.
      attr = self.ClassAttr(name, self)
      var.connect(attr)
      self.attrs[name] = attr
    return

  def fullname(self):
    return self.space.fullname()
  
  def show(self, p):
    p('### %s(%s)' % (self.loc._module.get_loc(), self.loc.lineno))
    for frame in self.frames:
      if frame.loc:
        p('# instantiated at %s(%d)' % (frame.loc._module.get_loc(), frame.loc.lineno))
    if self.bases:
      p('class %s(%s):' % (self.name, ', '.join( base.fullname() for base in self.baseklass.types )))
    else:
      p('class %s:' % self.name)
    blocks = set( name for (name,_) in self.children )
    for (name, attr) in sorted(self.attrs.iteritems()):
      if name in blocks or not attr.types: continue
      p('  class.%s = %s' % (name, attr.describe()))
    for (name, attr) in sorted(self.instance.attrs.iteritems()):
      if name in blocks or not attr.types: continue
      p('  instance.%s = %s' % (name, attr.describe()))
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
      instance.klass.connect(self, self.recv_baseklass)
      return

    def __repr__(self):
      return '%r.%s' % (self.instance, self.name)

    def recv(self, src):
      from function import FuncType, StaticMethodType, ClassMethodType 
      for obj in src:
        if obj in self.processed: continue
        self.processed.add(obj)
        if isinstance(obj, StaticMethodType):
          pass
        elif isinstance(obj, ClassMethodType):
          obj = self.klass.bind_func(obj)
        elif isinstance(obj, FuncType):
          obj = self.instance.bind_func(obj)
        self.update_type(obj)
      self.update_calls()
      return

  #
  def __init__(self, klass):
    self.klass = klass
    self.attrs = {}
    self.boundmethods = {}
    BuiltinObject.__init__(self, klass)
    for (name, value) in klass.attrs.iteritems():
      value.connect(self.get_attr(name))
    return
  
  def __repr__(self):
    return ('<instance %s>' % self.klass.fullname())
  
  def get_type(self):
    return self.klass

  def get_attr(self, name, write=False):
    if name not in self.attrs:
      attr = self.InstanceAttr(name, self)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def get_iter(self, frame):
    return self.get_attr('__iter__').optcall(frame, [], {})
  
  def bind_func(self, func):
    if func not in self.boundmethods:
      method = BoundMethodType(self, func)
      self.boundmethods[func] = method
    else:
      method = self.boundmethods[func]
    return method

class InstanceType(BuiltinType):
  TYPE_NAME = 'object'
