#!/usr/bin/env python

from typenode import TreeReporter, SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, \
     BuiltinType, BuiltinObject
from namespace import Namespace, Variable
from exception import TypeErrorType, ExceptionFrame


##  FuncType
##
class FuncType(BuiltinType, TreeReporter):

  TYPE_NAME = 'function'
  
  ##  FuncBody
  ##
  class FuncBody(CompoundTypeNode, ExceptionFrame):

    def __init__(self, name, loc):
      self.name = name
      ExceptionFrame.__init__(self, loc=loc)
      CompoundTypeNode.__init__(self)
      return

    def __repr__(self):
      return '<FuncBody %s>' % self.name

    def set_retval(self, evals):
      from aggregate_types import IterType
      returns = [ obj for (t,obj) in evals if t == 'r' ]
      yields = [ obj for (t,obj) in evals if t == 'y' ]
      assert returns
      if yields:
        retvals = [ IterType.get_object([ slot.value for slot in yields ]) ]
      else:
        retvals = returns
      for obj in retvals:
        obj.connect(self)
      return

  def __init__(self, parent_reporter, parent_frame, parent_space,
               name, argnames, defaults, varargs, kwargs, code, loc):
    from expression import TupleUnpack
    def maprec(func, x):
      if isinstance(x, tuple):
        return tuple( maprec(func, y) for y in x )
      else:
        return func(x)
    BuiltinType.__init__(self)
    TreeReporter.__init__(self, parent_reporter, name)
    self.name = name
    # prepare local variables that hold passed arguments.
    self.space = Namespace(parent_space, name)
    self.loc = loc
    # handle "**kwd".
    self.kwarg = None
    if kwargs:
      self.kwarg = argnames[-1]
      del argnames[-1]
      self.space.register_var(self.kwarg)
    # handle "*args".
    self.vararg = None
    if varargs:
      self.vararg = argnames[-1]
      del argnames[-1]
      self.space.register_var(self.vararg)
    # handle normal args.
    self.argnames = tuple(argnames)
    maprec(lambda argname: self.space.register_var(argname), self.argnames)
    self.argvars = maprec(lambda argname: self.space[argname], self.argnames)
    # assign the default values.
    self.defaults = tuple(defaults)
    def assign(var1, arg1):
      assert not isinstance(var1, list), var1
      assert not isinstance(arg1, list), arg1
      if isinstance(var1, tuple):
        tup = TupleUnpack(parent_frame, code, arg1, len(var1))
        for (i,v) in enumerate(var1):
          assign(v, tup.get_nth(i))
      else:
        arg1.connect(var1)
      return
    for (var1,arg1) in zip(self.argvars[-len(defaults):], self.defaults):
      assign(var1, arg1)
    # build the function body.
    self.body = self.build_body(name, code)
    self.callers = []
    return

  def build_body(self, name, tree):
    from syntax import build_stmt
    body = self.FuncBody(name, tree)
    evals = []
    self.space.register_names(tree)
    build_stmt(self, body, self.space, tree, evals, isfuncdef=True)
    body.set_retval(evals)
    return body

  def __repr__(self):
    return ('<Function %s>' % (self.name))

  def get_type(self):
    return self

  def call(self, frame, args, kwargs):
    from builtin_types import StrType
    from aggregate_types import DictType, TupleType
    from expression import TupleUnpack
    self.callers.append(frame)
    # Copy the list of argument variables.
    argvars = list(self.argvars)
    # Process keyword arguments first.
    varkwargs = CompoundTypeNode()
    for (kwname, kwvalue) in kwargs.iteritems():
      for var1 in argvars:
        if isinstance(var1, Variable) and var1.name == kwname:
          kwvalue.connect(var1)
          # When a keyword argument is given, remove that name from the remaining arguments.
          argvars.remove(var1)
          break
      else:
        if self.kwarg:
          kwvalue.connect(varkwargs)
        else:
          frame.raise_expt(TypeErrorType.occur('invalid keyword argument for %s: %r' % (self.name, kwname)))
    # Handle standard arguments.
    #
    # assign(var1,arg1):
    #  Assign a actual parameter arg1 to a local variable var1.
    def assign(var1, arg1):
      assert not isinstance(var1, list), var1
      assert not isinstance(arg1, list), arg1
      if isinstance(var1, tuple):
        tup = TupleUnpack(frame, None, arg1, len(var1))
        for (i,v) in enumerate(var1):
          assign(v, tup.get_nth(i))
      else:
        arg1.connect(var1)
      return
    varargs = []
    for arg1 in args:
      if argvars:
        var1 = argvars.pop(0)
        assign(var1, arg1)
      elif self.vararg:
        varargs.append(arg1)
      else:
        frame.raise_expt(TypeErrorType.occur('too many argument for %s: at most %d' % (self.name, len(self.argvars))))
    # Handle remaining arguments: kwargs and varargs.
    if self.kwarg:
      self.space[self.kwarg].bind(DictType.get_object(key=StrType.get_object(), value=varkwargs))
    if self.vararg:
      self.space[self.vararg].bind(TupleType.get_object(varargs))
    if len(self.defaults) < len(argvars):
      frame.raise_expt(TypeErrorType.occur('too few argument for %s: %d or more' % (self.name, len(argvars))))
    self.body.connect_expt(frame)
    return self.body

  def show(self, p):
    p('### %s(%s)' % (self.loc._module.get_loc(), self.loc.lineno))
    for frame in self.callers:
      if frame.loc:
        p('# called at %s(%s)' % (frame.loc._module.get_loc(), frame.loc.lineno))
    names = set()
    def recjoin(sep, seq):
      for x in seq:
        if isinstance(x, tuple):
          yield '(%s)' % sep.join(recjoin(sep, x))
        else:
          names.add(x)
          yield '%s=%s' % (x, self.space[x].describe())
      return
    r = list(recjoin(', ', self.argnames))
    if self.vararg:
      r.append('*'+self.vararg)
    if self.kwarg:
      r.append('**'+self.kwarg)
    p('def %s(%s):' % (self.name, ', '.join(r)) )
    names.update( name for (name,_) in self.children )
    for (k,v) in sorted(self.space):
      if k not in names:
        p('  %s = %s' % (k, v.describe()))
    p('  return %s' % self.body.describe())
    self.body.show(p)
    return


class StaticMethodType(FuncType): pass
class ClassMethodType(FuncType): pass


##  LambdaFuncType
##
class LambdaFuncType(FuncType):
  
  def __init__(self, parent_reporter, parent_frame, parent_space,
               argnames, defaults, varargs, kwargs, code, loc):
    name = '__lambda_%x' % id(code)
    FuncType.__init__(self, parent_reporter, parent_frame, parent_space,
                      name, argnames, defaults, varargs, kwargs, code, loc)
    return

  def build_body(self, name, tree):
    from syntax import build_expr
    body = self.FuncBody(name, tree)
    evals = []
    evals.append(('r', build_expr(self, body, self.space, tree, evals)))
    body.set_retval(evals)
    return body
  
  def __repr__(self):
    return ('<LambdaFunc %s>' % (self.name))


##  MethodType
##
class MethodType(BuiltinType):

  TYPE_NAME = 'method'

  def __init__(self, arg0, func):
    self.arg0 = arg0
    self.func = func
    BuiltinType.__init__(self)
    return

  def __repr__(self):
    return '<method %r(%s=%r)>' % (self.func, self.func.argnames[0], self.arg0)
  
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

    def __init__(self, name, klass, bases):
      CompoundTypeNode.__init__(self)
      self.name = name
      self.klass = klass
      self.bases = bases
      for base in bases:
        base.connect(self, self.recv_base)
      return

    def __repr__(self):
      return '%r.@%s' % (self.klass, self.name)

    def recv_base(self, src):
      for klass in src:
        try:
          klass.get_attr(self.name).connect(self)
        except NodeAttrError:
          pass
      return
  
  ##  OptionalAttr
  ##
  class OptionalAttr(CompoundTypeNode, ExceptionFrame):
    
    def __init__(self, instance, name):
      self.attr = instance.get_attr(name)
      self.args = []
      self.kwargs = {}
      self.retval = CompoundTypeNode()
      CompoundTypeNode.__init__(self)
      ExceptionFrame.__init__(self)
      self.attr.connect(self)
      return

    def __repr__(self):
      return repr(self.attr)

    def call(self, frame, args, kwargs):
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
      return self.retval
    
    def recv(self, src):
      for obj in src:
        try:
          # XXX self.kwargs might not be fixated.
          obj.call(self, self.args, self.kwargs).connect(self.retval)
        except NodeTypeError:
          self.update_type([obj])
      return

  ##  InitMethodBody
  ##
  class InitMethodBody(OptionalAttr, ExceptionFrame):

    def __init__(self, instance):
      ClassType.OptionalAttr.__init__(self, instance, '__init__')
      ExceptionFrame.__init__(self)
      self.update_types([instance])
      return

    def call(self, frame, args, kwargs):
      ClassType.OptionalAttr.call(self, frame, args, kwargs)
      return self

    def recv(self, _): # ignore return value
      return

  def __init__(self, parent_reporter, parent_frame, parent_space, name, bases, code, evals, loc):
    from syntax import build_stmt
    BuiltinType.__init__(self)
    TreeReporter.__init__(self, parent_reporter, name)
    self.name = name
    self.bases = bases
    self.loc = loc
    self.boundmethods = {}
    space = Namespace(parent_space, name)
    if code:
      space.register_names(code)
      build_stmt(self, parent_frame, space, code, evals)
    self.attrs = {}
    for (name,var) in space:
      # Do not inherit attributes from the base class
      # if they are explicitly overriden.
      attr = self.ClassAttr(name, self, [])
      var.connect(attr)
      self.attrs[name] = attr
    self.instance = InstanceObject(self)
    self.baseklass = CompoundTypeNode()
    for base in bases:
      base.connect(self.baseklass)
    self.callers = []
    return

  def __repr__(self):
    return ('<Class %s>' % (self.name,))

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
      attr = self.ClassAttr(name, self, self.bases)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def bind_func(self, func):
    if func not in self.boundmethods:
      method = MethodType(self, func)
      self.boundmethods[func] = method
    else:
      method = self.boundmethods[func]
    return method

  def call(self, frame, args, kwargs):
    self.callers.append(frame)
    return self.InitMethodBody(self.instance).call(frame, args, kwargs)
  
  def show(self, p):
    p('### %s(%s)' % (self.loc._module.get_loc(), self.loc.lineno))
    for frame in self.callers:
      if frame.loc:
        p('# called at %s(%d)' % (frame.loc._module.get_loc(), frame.loc.lineno))
    if self.bases:
      p('class %s(%s):' % (self.name, ', '.join( repr(base) for base in self.bases )))
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
  class InstanceAttr(CompoundTypeNode):

    def __init__(self, name, klass, instance):
      CompoundTypeNode.__init__(self)
      self.name = name
      self.klass = klass
      self.instance = instance
      self.processed = set()
      self.klass.connect(self, self.recv_klass)
      return

    def __repr__(self):
      return '%r.@%s' % (self.instance, self.name)

    def recv_klass(self, src):
      for obj in src:
        try:
          obj.get_attr(self.name).connect(self)
        except NodeAttrError:
          pass
      return

    def recv(self, src):
      for obj in src:
        if obj in self.processed: continue
        self.processed.add(obj)
        if isinstance(obj, StaticMethodType):
          pass
        elif isinstance(obj, ClassMethodType):
          obj = self.klass.bind_func(obj)
        elif isinstance(obj, FuncType):
          obj = self.instance.bind_func(obj)
        self.update_types([obj])
      return

  class InstanceOptAttr(InstanceAttr):
    pass
    
  def __init__(self, klass):
    SimpleTypeNode.__init__(self, self)
    self.klass = klass
    self.attrs = {}
    self.boundmethods = {}
    for (name, value) in klass.attrs.iteritems():
      value.connect(self.get_attr(name))
    return
  
  def __repr__(self):
    return ('<Instance %s>' % (self.klass.name,))
  
  def get_type(self):
    return self.klass

  def is_type(self, *typeobjs):
    for typeobj in typeobjs:
      if isinstance(typeobj, ClassType):
        return self.klass.is_subclass(typeobj)
    return BuiltinObject.is_type(self, *typeobjs)

  def get_attr(self, name, write=False):
    if name not in self.attrs:
      attr = self.InstanceAttr(name, self.klass, self)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def get_opt_attr(self, name):
    if name not in self.attrs:
      attr = self.InstanceOptAttr(name, self.klass, self)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def bind_func(self, func):
    if func not in self.boundmethods:
      method = MethodType(self, func)
      self.boundmethods[func] = method
    else:
      method = self.boundmethods[func]
    return method

class InstanceType(BuiltinType):
  TYPE_NAME = 'object'
  TYPE_INSTANCE = InstanceObject
