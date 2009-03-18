#!/usr/bin/env python

from typenode import CompoundTypeNode, \
     NodeTypeError, NodeAttrError, BuiltinType, BuiltinObject
from namespace import Namespace, Variable
from config import ErrorConfig
from module import TreeReporter
from frame import ExecutionFrame


# assign_arg(var1,arg1): Assign an argument to a local variable var1.
def assign_arg(frame, var1, arg1):
  from expression import TupleUnpack
  assert not isinstance(var1, list), var1
  assert not isinstance(arg1, list), arg1
  if isinstance(var1, tuple):
    tup = TupleUnpack(frame, arg1, len(var1))
    for (i,v) in enumerate(var1):
      assign_arg(frame, v, tup.get_nth(i))
  else:
    var1.bind(arg1)
  return


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
        obj.connect(self.recv)
      return

  def __init__(self, parent_reporter, parent_frame, parent_space,
               name, argnames, defaults, variargs, kwargs, code, tree):
    TreeReporter.__init__(self, parent_reporter, name)
    def maprec(func, x):
      if isinstance(x, tuple):
        return tuple( maprec(func, y) for y in x )
      else:
        return func(x)
    self.name = name
    # prepare local variables that hold passed arguments.
    self.space = Namespace(parent_space, name)
    self.frame = ExecutionFrame(None, tree)
    # handle "**kwd".
    self.kwarg = None
    if kwargs:
      self.kwarg = argnames[-1]
      del argnames[-1]
      self.space.register_var(self.kwarg)
    # handle "*args".
    self.variarg = None
    if variargs:
      self.variarg = argnames[-1]
      del argnames[-1]
      self.space.register_var(self.variarg)
    # handle normal args.
    self.argnames = tuple(argnames)
    maprec(lambda argname: self.space.register_var(argname), self.argnames)
    self.argvars = maprec(lambda argname: self.space[argname], self.argnames)
    # assign the default values.
    self.defaults = tuple(defaults)
    for (var1,arg1) in zip(self.argvars[-len(defaults):], self.defaults):
      assign_arg(parent_frame, var1, arg1)
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
    from expression import TupleUnpack, TupleSlice
    # Process keyword arguments first.
    varsleft = list(self.argvars)
    varikwargs = []
    for (kwname, kwvalue) in kwargs.iteritems():
      for var1 in varsleft:
        if isinstance(var1, Variable) and var1.name == kwname:
          var1.bind(kwvalue)
          # When a keyword argument is given, remove that name from the remaining arguments.
          varsleft.remove(var1)
          break
      else:
        if self.kwarg:
          varikwargs.append(kwvalue)
        else:
          frame.raise_expt(ErrorConfig.InvalidKeywordArgs(kwname))
    # Process standard arguments.
    variargs = []
    for arg1 in args:
      if varsleft:
        var1 = varsleft.pop(0)
        assign_arg(frame, var1, arg1)
      elif self.variarg:
        variargs.append(arg1)
      else:
        # Too many arguments.
        frame.raise_expt(ErrorConfig.InvalidNumOfArgs(len(self.argvars), len(args)))
    # Process a star.
    if star:
      tup = TupleUnpack(frame, star, len(varsleft), strict=not self.variarg)
      for (i,var1) in enumerate(varsleft):
        var1.bind(tup.get_nth(i))
      if self.variarg:
        left = TupleSlice(frame, star, len(varsleft))
        self.space[self.variarg].bind(TupleType.create_tuple(elemall=left))
    elif len(varsleft) - len(self.defaults):
      # Too few arguments.
      frame.raise_expt(ErrorConfig.InvalidNumOfArgs(len(self.defaults), len(args)))
    # Handle remaining arguments: kwargs and variargs.
    if self.variarg and variargs:
      self.space[self.variarg].bind(TupleType.create_tuple(CompoundTypeNode(variargs)))
    if self.kwarg:
      if varikwargs:
        self.space[self.kwarg].bind(DictType.create_dict(key=StrType.get_object(), value=CompoundTypeNode(varikwargs)))
      else:
        self.space[self.kwarg].bind(DictType.create_null())
    # Remember where this is called from.
    self.frames.add(frame)
    # Propagate the exceptions upward.
    self.frame.connect(frame.recv)
    return self.body

  def show(self, out):
    (module,lineno) = self.frame.getloc()
    out.write('### %s(%s)' % (module.get_path(), lineno))
    for frame in self.frames:
      (module,lineno) = frame.getloc()
      out.write('# called at %s(%s)' % (module.get_path(), lineno))
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
    if self.variarg:
      r.append('*'+self.variarg)
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
               argnames, defaults, variargs, kwargs, code, tree):
    name = '__lambda_%x' % id(code)
    FuncType.__init__(self, parent_reporter, parent_frame, parent_space,
                      name, argnames, defaults, variargs, kwargs, code, tree)
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


