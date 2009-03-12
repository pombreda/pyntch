#!/usr/bin/env python

from typenode import CompoundTypeNode, \
     NodeTypeError, NodeAttrError, BuiltinType, BuiltinObject
from namespace import Namespace, Variable
from exception import TypeErrorType
from module import TreeReporter
from frame import ExecutionFrame


##  FuncType
##
class FuncType(BuiltinType, TreeReporter):

  TYPE_NAME = 'function'
  
  ##  FuncBody
  ##
  class FuncBody(CompoundTypeNode):

    def __init__(self, name):
      self.name = name
      CompoundTypeNode.__init__(self)
      return

    def __repr__(self):
      return '<funcbody %s>' % self.name

    def set_retval(self, evals):
      from aggregate_types import GeneratorType
      returns = [ obj for (t,obj) in evals if t == 'r' ]
      yields = [ obj for (t,obj) in evals if t == 'y' ]
      assert returns
      if yields:
        retvals = [ GeneratorType.create_generator(CompoundTypeNode(yields)) ]
      else:
        retvals = returns
      for obj in retvals:
        obj.connect(self)
      return

  def __init__(self, parent_reporter, parent_frame, parent_space,
               name, argnames, defaults, varargs, kwargs, code, tree):
    TreeReporter.__init__(self, parent_reporter, name)
    from expression import TupleUnpack
    def maprec(func, x):
      if isinstance(x, tuple):
        return tuple( maprec(func, y) for y in x )
      else:
        return func(x)
    self.name = name
    # prepare local variables that hold passed arguments.
    self.space = Namespace(parent_space, name)
    self.frame = ExecutionFrame(parent_frame)
    self.loc = (tree._module, tree.lineno)
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
    self.frames = set()
    BuiltinType.__init__(self)
    return

  def build_body(self, name, tree):
    from syntax import build_stmt
    body = self.FuncBody(name)
    evals = []
    self.space.register_names(tree)
    build_stmt(self, self.frame, self.space, tree, evals, isfuncdef=True)
    body.set_retval(evals)
    return body

  def __repr__(self):
    return ('<function %s>' % self.fullname())

  def fullname(self):
    return self.space.fullname()

  def get_type(self):
    return self

  def call(self, frame, args, kwargs, star, dstar):
    from basic_types import StrType
    from aggregate_types import DictType, TupleType
    from expression import TupleUnpack
    assert isinstance(frame, ExecutionFrame)
    self.frames.add(frame)
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
        tup = TupleUnpack(frame, arg1, len(var1))
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
      self.space[self.kwarg].bind(DictType.create_dict(key=StrType.get_object(), value=varkwargs))
    if self.vararg:
      self.space[self.vararg].bind(TupleType.create_tuple(CompoundTypeNode(varargs)))
    if len(self.defaults) < len(argvars):
      frame.raise_expt(TypeErrorType.occur('too few argument for %s: %d or more' % (self.name, len(argvars))))
    return self.body

  def show(self, out):
    (module,lineno) = self.loc
    out.write('### %s(%s)' % (module.get_loc(), lineno))
    for frame in self.frames:
      (module,lineno) = frame.getloc()
      out.write('# called at %s(%s)' % (module.get_loc(), lineno))
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
    out.write('def %s(%s):' % (self.name, ', '.join(r)) )
    names.update( name for (name,_) in self.children )
    for (k,v) in sorted(self.space):
      if k not in names:
        out.write('  %s = %s' % (k, v.describe()))
    out.write('  return %s' % self.body.describe())
    self.frame.show(out)
    return


class StaticMethodType(FuncType): pass
class ClassMethodType(FuncType): pass


##  LambdaFuncType
##
class LambdaFuncType(FuncType):
  
  def __init__(self, parent_reporter, parent_frame, parent_space,
               argnames, defaults, varargs, kwargs, code, tree):
    name = '__lambda_%x' % id(code)
    FuncType.__init__(self, parent_reporter, parent_frame, parent_space,
                      name, argnames, defaults, varargs, kwargs, code, tree)
    return

  def build_body(self, name, tree):
    from syntax import build_expr
    body = self.FuncBody(name)
    evals = []
    evals.append(('r', build_expr(self, self.frame, self.space, tree, evals)))
    body.set_retval(evals)
    return body
  
  def __repr__(self):
    return ('<lambda %s>' % self.space.fullname())


