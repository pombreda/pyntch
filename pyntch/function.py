#!/usr/bin/env python

from typenode import TreeReporter, SimpleTypeNode, CompoundTypeNode, NodeTypeError
from namespace import Namespace, Variable
from exception import ExceptionType, ExceptionFrame


##  KeywordArg
##
class KeywordArg(SimpleTypeNode):

  def __init__(self, name, value):
    SimpleTypeNode.__init__(self)
    self.name = name
    self.value = value
    return

  def __repr__(self):
    return '%s=%r' % (self.name, self.value)


##  FuncType
##
class FuncType(SimpleTypeNode, TreeReporter):
  
  ##  FuncBody
  ##
  class FuncBody(CompoundTypeNode, ExceptionFrame):

    def __init__(self, name):
      CompoundTypeNode.__init__(self)
      ExceptionFrame.__init__(self)
      self.name = name
      return

    def __repr__(self):
      return '<FuncBody %s>' % self.name

    def set_retval(self, evals):
      from builtin_types import IterType
      returns = [ obj for (t,obj) in evals if t == 'r' ]
      yields = [ obj for (t,obj) in evals if t == 'y' ]
      assert returns
      if yields:
        retvals = [ IterType([ slot.value for slot in yields ]) ]
      else:
        retvals = returns
      for obj in retvals:
        obj.connect(self)
      return

  def __init__(self, parent_reporter, parent_frame, parent_space,
               name, argnames, defaults, varargs, kwargs, code):
    from builtin_types import TupleUnpack
    def maprec(func, x):
      if isinstance(x, tuple):
        return tuple( maprec(func, y) for y in x )
      else:
        return func(x)
    SimpleTypeNode.__init__(self)
    TreeReporter.__init__(self, parent_reporter, name)
    self.name = name
    # prepare local variables that hold passed arguments.
    self.space = Namespace(parent_space, name)
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
        tup = TupleUnpack(parent_frame, arg1, len(var1))
        for (i,v) in enumerate(var1):
          assign(v, tup.get_nth(i))
      else:
        arg1.connect(var1)
      return
    for (var1,arg1) in zip(self.argvars[-len(defaults):], self.defaults):
      assign(var1, arg1)
    # build the function body.
    self.body = self.build_body(name, code)
    return

  def build_body(self, name, tree):
    from syntax import build_stmt
    body = self.FuncBody(name)
    evals = []
    self.space.register_names(tree)
    build_stmt(self, body, self.space, tree, evals, isfuncdef=True)
    body.set_retval(evals)
    return body

  def __repr__(self):
    return ('<Function %s>' % (self.name))

  def call(self, caller, args):
    from builtin_types import StrType, DictType, TupleType, TupleUnpack
    # bind args.
    def assign(var1, arg1):
      assert not isinstance(var1, list), var1
      assert not isinstance(arg1, list), arg1
      if isinstance(arg1, KeywordArg):
        name = arg1.name
        if name not in self.space:
          caller.raise_expt(ExceptionType(
            'TypeError',
            'invalid argname: %r' % name))
        else:
          arg1.value.connect(self.space[name])
      elif isinstance(var1, tuple):
        tup = TupleUnpack(caller, arg1, len(var1))
        for (i,v) in enumerate(var1):
          assign(v, tup.get_nth(i))
      else:
        arg1.connect(var1)
      return
    argvars = list(self.argvars)
    kwargs = []
    varargs = []
    for arg1 in args:
      if isinstance(arg1, KeywordArg):
        (name, value) = (arg1.name, arg1.value)
        if name in [ var1.name for var1 in argvars if isinstance(var1, Variable) ]:
          value.connect(self.space[name])
          argvars = [ var1 for var1 in argvars
                      if not isinstance(var1, Variable) or var1.name != name ]
        elif self.kwarg:
          kwargs.append(value)
        else:
          caller.raise_expt(ExceptionType(
            'TypeError',
            'invalid keyword argument: %r' % name))
      elif argvars:
        var1 = argvars.pop(0)
        assign(var1, arg1)
      elif self.vararg:
        varargs.append(arg1)
      else:
        caller.raise_expt(ExceptionType(
          'TypeError',
          'too many argument: more than %r' % len(self.argvars)))
    if kwargs:
      self.space[self.kwarg].bind(DictType([ (StrType.get(), obj) for obj in kwargs ]))
    if varargs:
      self.space[self.vararg].bind(TupleType(tuple(varargs)))
    if argvars:
      caller.raise_expt(ExceptionType(
        'TypeError',
        'too few argument: %r more' % (len(argvars))))
    return self.body

  def show(self, p):
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
               argnames, defaults, varargs, kwargs, code):
    name = '__lambda_%x' % id(code)
    FuncType.__init__(self, parent_reporter, parent_frame, parent_space,
                      name, argnames, defaults, varargs, kwargs, code)
    return

  def build_body(self, name, tree):
    from syntax import build_expr
    body = self.FuncBody(name)
    evals = []
    evals.append(('r', build_expr(self, body, self.space, tree, evals)))
    body.set_retval(evals)
    return body
  
  def __repr__(self):
    return ('<LambdaFunc %s>' % (self.name))


##  BoundMethod
##
class BoundMethod(SimpleTypeNode):

  def __init__(self, arg0, func):
    self.arg0 = arg0
    self.func = func
    SimpleTypeNode.__init__(self)
    return

  def __repr__(self):
    return '<Bound %r(%s=%r)>' % (self.func, self.func.argnames[0], self.arg0)

  def call(self, caller, args):
    return self.func.call(caller, (self.arg0,)+tuple(args))


##  ClassType
##
class ClassType(SimpleTypeNode, TreeReporter):
  
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
      for klass in src.types:
        klass.get_attr(self.name).connect(self)
      return

  ##  OptionalMethod
  ##
  class OptionalMethod(CompoundTypeNode):
    pass
  
  ##  OptionalAttr
  ##
  class OptionalAttr(CompoundTypeNode):
    
    def __init__(self, instance, name):
      CompoundTypeNode.__init__(self)
      self.binds = []
      self.method = instance.get_attr(name)
      self.method.connect(self, self.recv_method)
      self.body = ClassType.OptionalMethod()
      return

    def __repr__(self):
      return repr(self.method)

    def call(self, caller, args):
      self.binds.append((caller, args))
      self.recv_method(self.method)
      return self.body

    def recv_method(self, src):
      for func in src.types:
        for (caller,args) in self.binds:
          try:
            result = func.call(caller, args)
            result.connect(self.body)
          except NodeTypeError:
            caller.raise_expt(ExceptionType(
              'TypeError',
              'cannot call: %r might be %r' % (src, func)
              ))
      return

  ##  InitMethodBody
  ##
  class InitMethodBody(OptionalAttr, ExceptionFrame):

    def __init__(self, instance):
      ClassType.OptionalAttr.__init__(self, instance, '__init__')
      ExceptionFrame.__init__(self)
      self.types.add(instance)
      return

    def call(self, caller, args):
      ClassType.OptionalAttr.call(self, caller, args)
      return self

    def recv(self, _): # ignore return value
      return

  def __init__(self, parent_reporter, parent_frame, parent_space, name, bases, code, evals):
    from syntax import build_stmt
    SimpleTypeNode.__init__(self)
    TreeReporter.__init__(self, parent_reporter, name)
    self.name = name
    self.bases = bases
    self.boundmethods = {}
    space = Namespace(parent_space, name)
    if code:
      space.register_names(code)
      build_stmt(self, parent_frame, space, code, evals)
    self.attrs = {}
    for (name,var) in space:
      attr = self.ClassAttr(name, self, self.bases)
      var.connect(attr)
      self.attrs[name] = attr
    self.instance = InstanceType(self)
    return

  def __repr__(self):
    return ('<Class %s>' % (self.name,))

  def get_attr(self, name):
    if name not in self.attrs:
      attr = self.ClassAttr(name, self, self.bases)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def bind_func(self, func):
    if func not in self.boundmethods:
      method = BoundMethod(self, func)
      self.boundmethods[func] = method
    else:
      method = self.boundmethods[func]
    return method

  def call(self, caller, args):
    return self.InitMethodBody(self.instance).call(caller, args)
  
  def show(self, p):
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
class InstanceType(SimpleTypeNode):
  
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
      for obj in src.types:
        obj.get_attr(self.name).connect(self)
      return

    def recv(self, src):
      types = set()
      for obj in src.types:
        if obj in self.processed: continue
        self.processed.add(obj)
        if isinstance(obj, StaticMethodType):
          pass
        elif isinstance(obj, ClassMethodType):
          obj = self.klass.bind_func(obj)
        elif isinstance(obj, FuncType):
          obj = self.instance.bind_func(obj)
        types.add(obj)
      self.update_types(types)
      return

  class InstanceOptAttr(InstanceAttr):
    pass
    
  def __init__(self, klass):
    SimpleTypeNode.__init__(self)
    self.klass = klass
    self.attrs = {}
    self.boundmethods = {}
    for (name, value) in klass.attrs.iteritems():
      value.connect(self.get_attr(name))
    return
  
  def __repr__(self):
    return ('<Instance %s>' % (self.klass.name,))

  def get_attr(self, name):
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
      method = BoundMethod(self, func)
      self.boundmethods[func] = method
    else:
      method = self.boundmethods[func]
    return method
