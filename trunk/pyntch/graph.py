#!/usr/bin/env python

import sys
from compiler import ast, parseFile
stdout = sys.stdout
stderr = sys.stderr
debug = 0


# TODO:
#  hierarchical types (to handle exception catching)
#  hierarchical packages
#  builtin functions
#  builtin type methods
#  +=
#  __add__ etc.
#  automatic coercion

def maprec(func, x):
  if isinstance(x, tuple):
    return tuple( maprec(func, y) for y in x )
  else:
    return func(x)

def recjoin(sep, seq):
  for x in seq:
    if isinstance(x, tuple):
      yield '(%s)' % sep.join(recjoin(sep, x))
    else:
      yield str(x)
  return


##  TreeReporter
##
class TreeReporter(object):

  def __init__(self, parent=None):
    self.children = []
    if parent:
      parent.children.append(self)
    return

  def show(self, p):
    return

  def showrec(self, out, i=0):
    h = '  '*i
    self.show(lambda s: out.write(h+s+'\n'))
    out.write('\n')
    for reporter in self.children:
      reporter.showrec(out, i+1)
    return
  
  

##  TypeNode
##
class NodeError(Exception): pass
class NodeTypeError(NodeError): pass
class InvalidMethodError(NodeError): pass

class TypeNode(object):

  def __init__(self, types):
    self.types = set(types)
    self.sendto = []
    return

  def connect(self, node, receiver=None):
    #assert isinstance(node, CompoundTypeNode), node
    if debug:
      print >>stderr, 'connect: %r :- %r' % (node, self)
    self.sendto.append((node, receiver))
    (receiver or node.recv)(self)
    return

  def recv(self, src):
    raise TypeError('TypeNode cannot receive a value.')

  def call(self, caller, args):
    raise NodeTypeError('not callable')
  def get_attr(self, name):
    raise NodeTypeError('no attribute')
  def get_element(self, subs, write=False):
    raise NodeTypeError('not subscriptable')
  def get_iter(self):
    raise NodeTypeError('not iterator')
  
  def describe(self):
    return self.desc1(set())
  def desc1(self, _):
    raise NotImplementedError


##  SimpleTypeNode
##
class SimpleTypeNode(TypeNode):

  NAME = None

  def __init__(self):
    TypeNode.__init__(self, [self])
    return

  def __repr__(self):
    raise NotImplementedError, self.__class__

  def desc1(self, _):
    return repr(self)


##  CompoundTypeNode
##
class CompoundTypeNode(TypeNode):

  def __init__(self):
    TypeNode.__init__(self, [])
    return

  def desc1(self, done):
    if self in done:
      return '...'
    else:
      done.add(self)
      return ('{%s}' % '|'.join( obj.desc1(done) for obj in self.types ))
                                  
  def recv(self, src):
    self.update_types(src.types)
    return

  def update_types(self, types):
    if types.difference(self.types):
      self.types.update(types)
      for (node,receiver) in self.sendto:
        (receiver or node.recv)(self)
    return


##  ExceptionFrame
##
##  An ExceptionFrame object is a place where an exception belongs.
##  Normally it's a body of function. Exceptions that are raised
##  within this frame are propagated to other ExceptionFrames which
##  invoke the function.
##
class ExceptionFrame(object):

  def __init__(self):
    self.expts = set()
    self.callers = []
    return

  def connect_expt(self, frame):
    assert isinstance(frame, ExceptionFrame)
    self.callers.append(frame)
    if debug:
      print >>stderr, 'connect_expt: %r :- %r' % (frame, self)
    self.propagate_expts(self.expts)
    return
  
  def add_expt(self, loc, expt):
    expt.loc = loc
    if debug:
      print >>stderr, 'add_expt: %r <- %r' % (self, expt)
    expt.connect(self, self.recv_expt)
    return

  def recv_expt(self, expt):
    if expt in self.expts: return
    self.expts.update(expt.types)
    self.propagate_expts(self.expts)
    return
  
  def propagate_expts(self, expts):
    for frame in self.callers:
      frame.update_expts(expts)
    return

  def update_expts(self, expts):
    if expts.difference(self.expts):
      self.expts.update(expts)
      self.propagate_expts(self.expts)
    return

  def show(self, p):
    for expt in self.expts:
      p(' raises %r' % expt)
    return


##  ExceptionCatcher
##
class ExceptionCatcher(ExceptionFrame):
  
  def __init__(self, parent):
    ExceptionFrame.__init__(self)
    self.handlers = {}
    self.catchall = False
    ExceptionFrame.connect_expt(self, parent)
    return
  
  def __repr__(self):
    if self.catchall:
      return '<except all>'
    else:
      return '<except %s>' % ', '.join(map(repr, self.handlers.iterkeys()))

  def add_all(self):
    self.catchall = True
    return
  
  def add_handler(self, expt):
    if expt not in self.handlers:
      self.handlers[expt] = (CompoundTypeNode(), CompoundTypeNode())
    expt.connect(self, self.recv_handler_expt)
    (_,var) = self.handlers[expt]
    return var

  def recv_handler_expt(self, src):
    (t,_) = self.handlers[src]
    for expt in src.types:
      if isinstance(expt, TupleType):
        expt.get_element(None).connect(t)
      else:
        expt.connect(t)
    return

  def propagate_expts(self, expts):
    if self.catchall: return
    remainder = set()
    for expt in expts:
      for (t,var) in self.handlers.itervalues():
        if t == expt: # XXX support hierarchical type
          expt.connect(var)
          break
      else:
        remainder.add(expt)
    ExceptionFrame.propagate_expts(self, remainder)
    return


##  ExceptionRaiser
##
class ExceptionRaiser(ExceptionFrame):

  nodes = None

  def __init__(self, parent, loc=None):
    ExceptionFrame.__init__(self)
    assert not loc or isinstance(loc, ast.Node)
    self.loc = loc
    ExceptionFrame.connect_expt(self, parent)
    ExceptionRaiser.nodes.append(self)
    return
  
  def raise_expt(self, expt):
    ExceptionFrame.add_expt(self, self.loc, expt)
    return
  
  def finish(self):
    return
  
  ###
  @classmethod
  def reset(klass):
    klass.nodes = []
    return
  
  @classmethod
  def runall(klass):
    for node in klass.nodes:
      node.finish()
    return


##  UndefinedTypeNode
##
class UndefinedTypeNode(TypeNode):
  
  def __init__(self, name):
    TypeNode.__init__(self, [])
    return
  
  def __repr__(self):
    return '(undef)'
  
  def desc1(self, _):
    return '(undef)'


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


##  TypeFilter
##
class TypeFilter(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent, *typeobjs):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent)
    self.typeobjs = typeobjs
    self.validtypes = set()
    for obj in typeobjs:
      obj.connect(self, self.recv_typeobj)
    return

  def __repr__(self):
    return ('<TypeFilter: %s: %s>' % 
            (','.join(map(repr, self.typeobjs)),
             '|'.join(map(repr, self.validtypes))))

  def recv_typeobj(self, src):
    self.validtypes.update(src.types)
    return
  
  def recv(self, src):
    types = set()
    validtypes = set( obj.typeobj for obj in self.validtypes )
    for obj in src.types:
      if obj in validtypes:
        types.add(obj)
      else:
        self.raise_expt(ExceptionType(
          'TypeError',
          '%r not type in %r' % (obj, validtypes)))
    self.update_types(types)
    return


##  ExceptionType
##
class ExceptionType(SimpleTypeNode):

  def __init__(self, name, msg, loc=None):
    SimpleTypeNode.__init__(self)
    assert not loc or isinstance(loc, ast.Node), loc
    self.loc = loc
    self.name = name
    self.msg = msg
    return

  def __repr__(self):
    if self.loc:
      return '<%s: %s> at %s(%d)' % (self.name, self.msg, self.loc._modname, self.loc.lineno)
    else:
      return '<%s: %s>' % (self.name, self.msg)

##  ExptMaker
##  Special behaviour on raising an exception.
##
class ExptMaker(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, exctype, excargs):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.exctype = exctype
    self.excargs = excargs
    exctype.connect(self, self.recv_type)
    return
  
  def __repr__(self):
    return '<exception %r(%s)>' % (self.exctype, ','.join(map(repr, self.excargs)))

  def recv_type(self, src):
    for obj in src.types:
      # Instantiate an object only if it is a class object.
      # Otherwise, just return the object given.
      if isinstance(obj, ClassType):
        try:
          result = obj.call(self, self.excargs)
        except NodeTypeError:
          self.raise_expt(ExceptionType(
            'TypeError',
            'cannot call: %r might be %r' % (self.exctype, obj)))
          continue
        for parent in self.callers:
          result.connect_expt(parent)
        result.connect(self)
      else:
        obj.connect(self)
    return


##  Variable
##
class Variable(CompoundTypeNode):

  def __init__(self, space, name):
    self.space = space
    self.name = name
    CompoundTypeNode.__init__(self)
    return
  
  def __repr__(self):
    return '@'+self.name

  def fullname(self):
    return '%s.%s' % (self.space.name, self.name)

  def bind(self, obj):
    obj.connect(self)
    return

  
##  Namespace
##
class Namespace:

  def __init__(self, parent_space, name):
    self.parent_space = parent_space
    self.name = name
    self.vars = {}
    self.msgs = []
    if parent_space:
      self.name = parent_space.name+'.'+name
    return
  
  def __repr__(self):
    return '<Namespace: %s>' % self.name

  def __contains__(self, name):
    return name in self.vars
  
  def __getitem__(self, name):
    return self.get_var(name)

  def __iter__(self):
    return self.vars.iteritems()

  def get_var(self, name):
    while self:
      if name in self.vars:
        return self.vars[name]
      self = self.parent_space
    raise KeyError(name)

  def register_var(self, name):
    if name not in self.vars:
      var = Variable(self, name)
      self.vars[name] = var
    else:
      var = self.vars[name]
    return var
  
  # register_names
  def register_names(self, tree):
    # global
    if isinstance(tree, ast.Global):
      for name in tree.names:
        pass # XXX

    # def
    elif isinstance(tree, ast.Function):
      self.register_var(tree.name)
      for value in tree.defaults:
        self.register_names(value)
    # class
    elif isinstance(tree, ast.Class):
      self.register_var(tree.name)
      for base in tree.bases:
        self.register_names(base)
    # assign
    elif isinstance(tree, ast.Assign):
      for v in tree.nodes:
        self.register_names(tree.expr)
        self.register_names(v)
    elif isinstance(tree, ast.AugAssign):
      self.register_names(tree.expr)
    elif isinstance(tree, ast.AssTuple):
      for c in tree.nodes:
        self.register_names(c)
    elif isinstance(tree, ast.AssList):
      for c in tree.nodes:
        self.register_names(c)
    elif isinstance(tree, ast.AssName):
      self.register_var(tree.name)
    elif isinstance(tree, ast.AssAttr):
      pass
    elif isinstance(tree, ast.Subscript):
      self.register_names(tree.expr)
      for sub in tree.subs:
        self.register_names(sub)

    # return
    elif isinstance(tree, ast.Return):
      self.register_names(tree.value)

    # yield (for both python 2.4 and 2.5)
    elif isinstance(tree, ast.Yield):
      self.register_names(tree.value)

    # (mutliple statements)
    elif isinstance(tree, ast.Stmt):
      for stmt in tree.nodes:
        self.register_names(stmt)

    # if, elif, else
    elif isinstance(tree, ast.If):
      for (expr,stmt) in tree.tests:
        self.register_names(expr)
        self.register_names(stmt)
      if tree.else_:
        self.register_names(tree.else_)

    # for
    elif isinstance(tree, ast.For):
      self.register_names(tree.list)
      self.register_names(tree.assign)
      self.register_names(tree.body)
      if tree.else_:
        self.register_names(tree.else_)

    # while
    elif isinstance(tree, ast.While):
      self.register_names(tree.test)
      self.register_names(tree.body)
      if tree.else_:
        self.register_names(tree.else_)

    # try ... except
    elif isinstance(tree, ast.TryExcept):
      self.register_names(tree.body)
      for (expr,e,stmt) in tree.handlers:
        if expr:
          self.register_names(expr)
        if e:
          self.register_var(e.name)
        self.register_names(stmt)
      if tree.else_:
        self.register_names(tree.else_)

    # try ... finally
    elif isinstance(tree, ast.TryFinally):
      self.register_names(tree.body)
      self.register_names(tree.final)

    # raise
    elif isinstance(tree, ast.Raise):
      if tree.expr1:
        self.register_names(tree.expr1)
      if tree.expr2:
        self.register_names(tree.expr2)
        
    # import
    elif isinstance(tree, ast.Import):
      for (modname,name) in tree.names:
        asname = name or modname
        module = load_module(modname)
        self.register_var(asname)
        self[asname].bind(module)

    # from
    elif isinstance(tree, ast.From):
      module = load_module(tree.modname)
      for (name0,name1) in tree.names:
        if name0 == '*':
          self.import_all(module.space)
        else:
          asname = name1 or name0
          self.register_var(asname)
          self[asname].bind(module)

    # printnl
    elif isinstance(tree, ast.Printnl):
      for node in tree.nodes:
        self.register_names(node)
    
    # discard
    elif isinstance(tree, ast.Discard):
      self.register_names(tree.expr)

    # other statements
    elif isinstance(tree, ast.Break):
      pass
    elif isinstance(tree, ast.Continue):
      pass
    elif isinstance(tree, ast.Assert):
      pass
    elif isinstance(tree, ast.Print):
      pass
    elif isinstance(tree, ast.Yield):
      pass
    elif isinstance(tree, ast.Pass):
      pass

    # expressions
    elif isinstance(tree, ast.Const):
      pass
    elif isinstance(tree, ast.Name):
      pass
    elif isinstance(tree, ast.CallFunc):
      self.register_names(tree.node)
      for arg1 in tree.args:
        self.register_names(arg1)
    elif isinstance(tree, ast.Keyword):
      self.register_names(tree.expr)
    elif isinstance(tree, ast.Getattr):
      self.register_names(tree.expr)
    elif isinstance(tree, ast.Slice):      
      self.register_names(tree.expr)
      if tree.lower:
        self.register_names(tree.lower)
      if tree.upper:
        self.register_names(tree.upper)
    elif isinstance(tree, ast.Tuple):
      for node in tree.nodes:
        self.register_names(node)
    elif isinstance(tree, ast.List):
      for node in tree.nodes:
        self.register_names(node)
    elif isinstance(tree, ast.Dict):
      for (k,v) in tree.items:
        self.register_names(k)
        self.register_names(v)
    elif (isinstance(tree, ast.Add) or isinstance(tree, ast.Sub) or
          isinstance(tree, ast.Mul) or isinstance(tree, ast.Div) or
          isinstance(tree, ast.Mod) or isinstance(tree, ast.FloorDiv) or
          isinstance(tree, ast.LeftShift) or isinstance(tree, ast.RightShift) or
          isinstance(tree, ast.Power) or isinstance(tree, ast.Bitand) or
          isinstance(tree, ast.Bitor) or isinstance(tree, ast.Bitxor)):
      self.register_names(tree.left)
      self.register_names(tree.right)
    elif isinstance(tree, ast.Compare):
      self.register_names(tree.expr)
      for (_,node) in tree.ops:
        self.register_names(node)
    elif (isinstance(tree, ast.UnaryAdd) or isinstance(tree, ast.UnarySub)):
      self.register_names(tree.expr)
    elif (isinstance(tree, ast.And) or isinstance(tree, ast.Or)):
      for node in tree.nodes:
        self.register_names(node)
    elif isinstance(tree, ast.Not):
      self.register_names(tree.expr)
    elif isinstance(tree, ast.Lambda):
      for value in tree.defaults:
        self.register_names(value)

    # list comprehension
    elif isinstance(tree, ast.ListComp):
      self.register_names(tree.expr)
      for qual in tree.quals:
        self.register_names(qual.list)
        self.register_names(qual.assign)
        for qif in qual.ifs:
          self.register_names(qif.test)
    
    else:
      raise SyntaxError('unsupported syntax: %r' % tree)
    return

  def import_all(self, space):
    for (k,v) in space.vars.iteritems():
      self.vars[k] = v
    return


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
      returns = [ obj for (t,obj) in evals if t == 'r' ]
      yields = [ obj for (t,obj) in evals if t == 'y' ]
      assert returns
      if yields:
        retvals = [ Generator(yields) ]
      else:
        retvals = returns
      for obj in retvals:
        obj.connect(self)
      return

  def __init__(self, parent_reporter, parent_frame, parent_space,
               name, argnames, defaults, varargs, kwargs, code):
    SimpleTypeNode.__init__(self)
    TreeReporter.__init__(self, parent_reporter)
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
        tup = TupleUnpack(parent_frame, arg1.tree, arg1, len(var1))
        for (i,v) in enumerate(var1):
          assign(v, tup.get_element(i))
      else:
        arg1.connect(var1)
      return
    for (var1,arg1) in zip(self.argvars[-len(defaults):], self.defaults):
      assign(var1, arg1)
    # build the function body.
    self.body = self.build_body(name, code)
    return

  def build_body(self, name, tree):
    body = self.FuncBody(name)
    evals = []
    self.space.register_names(tree)
    build_stmt(self, body, self.space, tree, evals, isfuncdef=True)
    body.set_retval(evals)
    return body

  def __repr__(self):
    return ('<Function %s>' % (self.name))

  def call(self, caller, args):
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
        tup = TupleUnpack(caller, arg1.tree, arg1, len(var1))
        for (i,v) in enumerate(var1):
          assign(v, tup.get_element(i))
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
        'not enough argument: %r more' % (len(argvars))))
    return self.body

  def show(self, p):
    r = list(recjoin(', ', self.argnames))
    if self.vararg:
      r.append('*'+self.vararg)
    if self.kwarg:
      r.append('**'+self.kwarg)
    p('def %s(%s):' % (self.name, ', '.join(r)) )
    for (k,v) in sorted(self.space):
      p(' %s = %s' % (k, v.describe()))
    self.body.show(p)
    p(' return %s' % self.body.describe())
    return


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
    body = self.FuncBody(name)
    evals = []
    evals.append(('r', build_expr(self, body, self.space, tree, evals)))
    body.set_retval(evals)
    return body
  
  def __repr__(self):
    return ('<LambdaFunc %s>' % (self.name))


##  ConstFuncType
##
class ConstFuncType(SimpleTypeNode):

  def __init__(self, obj):
    SimpleTypeNode.__init__(self)
    self.obj = obj
    return

  def __repr__(self):
    return '<Const %r>' % self.obj

  def connect_expt(self, frame):
    return
  
  def call(self, caller, args):
    return self.obj


##  FunCall
##
class FunCall(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, func, args):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.func = func
    self.args = args
    func.connect(self, self.recv_func)
    return

  def __repr__(self):
    return '<%r(%s)>' % (self.func, ','.join(map(repr, self.args)))

  def recv_func(self, src):
    for func in src.types:
      try:
        result = func.call(self, self.args)
        result.connect_expt(self)
        result.connect(self)
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'TypeError',
          'cannot call: %r might be %r' % (self.func, func)))
    return


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

    def __repr__(self):
      return '<__init__ %r>' % self.instance

    def call(self, caller, args):
      ClassType.OptionalAttr.call(self, caller, args)
      return self

    def recv(self, _): # ignore return value
      return

  def __init__(self, parent_reporter, parent_frame, parent_space, name, bases, code, evals):
    SimpleTypeNode.__init__(self)
    TreeReporter.__init__(self, parent_reporter)
    self.name = name
    self.bases = bases
    self.space = Namespace(parent_space, name)
    self.attrs = {}
    if code:
      self.space.register_names(code)
      build_stmt(self, parent_frame, self.space, code, evals)
    self.instance = InstanceType(self)
    return

  def __repr__(self):
    return ('<Class %s>' % (self.name,))

  def get_attr(self, name):
    if name not in self.attrs:
      attr = self.ClassAttr(name, self, self.bases)
      self.attrs[name] = attr
      try:
        self.space[name].connect(attr)
      except KeyError:
        pass
    else:
      attr = self.attrs[name]
    return attr

  def call(self, caller, args):
    return self.InitMethodBody(self.instance).call(caller, args)
  
  def show(self, p):
    p('class %s:' % self.name)
    for (_, attr) in sorted(self.attrs.iteritems()):
      p(' class.%s = %s' % (attr.name, attr.describe()))
    for (_, attr) in sorted(self.instance.attrs.iteritems()):
      p(' instance.%s = %s' % (attr.name, attr.describe()))
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
        if isinstance(obj, FuncType):
          obj = self.instance.bind_func(obj)
        # XXX
        #elif isinstance(obj, ClassMethodType):
        #elif isinstance(obj, StaticMethodType):
        types.add(obj)
      self.update_types(types)
      return

  class InstanceOptAttr(InstanceAttr):
    pass
    
  ##  BoundMethodType
  ##
  class BoundMethodType(SimpleTypeNode):

    def __init__(self, arg0, func):
      self.arg0 = arg0
      self.func = func
      SimpleTypeNode.__init__(self)
      return

    def __repr__(self):
      return '<Bound %r(%s=%r)>' % (self.func, self.func.argnames[0], self.arg0)

    def __eq__(self, obj):
      return (isinstance(obj, self.__class__) and
              self.arg0 == obj.arg0 and
              self.func == obj.func)
    def __hash__(self):
      return hash((self.arg0, self.func))

    def call(self, caller, args):
      return self.func.call(caller, (self.arg0,)+tuple(args))

  def __init__(self, klass):
    SimpleTypeNode.__init__(self)
    self.klass = klass
    self.boundfuncs = {}
    self.attrs = {}
    for (name, value) in klass.space:
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
    if func not in self.boundfuncs:
      method = self.BoundMethodType(self, func)
      self.boundfuncs[func] = method
    else:
      method = self.boundfuncs[func]
    return method
      

##  AttrRef
##
class AttrRef(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, attrname):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target = target
    self.attrname = attrname
    self.objs = set()
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return '%r.%s' % (self.target, self.attrname)

  def recv_target(self, src):
    self.objs.update(src.types)
    for obj in self.objs:
      try:
        attr = obj.get_attr(self.attrname)
        attr.connect(self)
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'AttributeError',
          'cannot get attribute: %r might be %r, no attr %s' % (self.target, obj, self.attrname)))
    return

  def finish(self):
    if not self.types:
      self.raise_expt(ExceptionType(
        'AttributeError',
        'attribute not defined: %r.%s' % (self.target, self.attrname)))
    return


##  AttrAssign
##
class AttrAssign(CompoundTypeNode):
  
  def __init__(self, tree, target, attrname, value):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.target = target
    self.objs = set()
    self.attrname = attrname
    self.value = value
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r.%s, %r)' % (self.target, self.attrname, self.value)

  def recv_target(self, src):
    self.objs.update(src.types)
    for obj in self.objs:
      attr = obj.get_attr(self.attrname)
      self.value.connect(attr)
    return


##  BinaryOp
##
class BinaryOp(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, op, left, right):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.op = op
    self.left_types = set()
    self.right_types = set()
    self.combinations = set()
    left.connect(self, self.recv_left)
    right.connect(self, self.recv_right)
    return
  
  def __repr__(self):
    return '%s(%r,%r)' % (self.op, self.left_types, self.right_types)

  def recv_left(self, src):
    self.left_types.update(src.types)
    self.update()
    return
  def recv_right(self, src):
    self.right_types.update(src.types)
    self.update()
    return

  VALID_TYPES = {
    ('str', 'Mul', 'int'): 'str',
    ('unicode', 'Mul', 'int'): 'unicode',
    }
  def update(self):
    for lobj in self.left_types:
      for robj in self.right_types:
        if (lobj,robj) in self.combinations: continue
        self.combinations.add((lobj,robj))
        if (isinstance(lobj, NumberType) and
            isinstance(robj, NumberType)):
          if self.op in ('Add','Sub','Mul','Div','Mod','FloorDiv'):
            if lobj.rank < robj.rank:
              self.update_types(set([robj]))
            else:
              self.update_types(set([lobj]))
            continue
        if (isinstance(lobj, BaseStringType) and
            isinstance(robj, BaseStringType) and
            self.op == 'Add'):
          self.update_types(set([robj]))
          continue
        k = (lobj.NAME, self.op, robj.NAME)
        if k in self.VALID_TYPES:
          v = BUILTIN_TYPE[self.VALID_TYPES[k]]
          self.update_types(set([v]))
          continue
        self.raise_expt(ExceptionType(
          'TypeError',
          'unsupported operand %s for %r and %r' % (self.op, lobj, robj)))
    return

class AssignOp(BinaryOp): pass


##  CompareOp
##
class CompareOp(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, expr0, comps):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.types.add(BoolType.get())
    self.expr0 = expr0
    self.comps = comps
    self.expr0.connect(self)
    for (_,expr) in self.comps:
      expr.connect(self)
    return
  
  def __repr__(self):
    return 'cmp(%r %s)' % (self.expr0,
                           ','.join( '%s %r' % (op,expr) for (op,expr) in self.comps ))
  
  def recv(self, _):
    # ignore because CompareOp always returns bool.
    return


##  BooleanOp
##
class BooleanOp(CompoundTypeNode):
  
  def __init__(self, op, nodes):
    CompoundTypeNode.__init__(self)
    self.types.add(BoolType.get())
    self.op = op
    self.nodes = nodes
    for node in self.nodes:
      node.connect(self)
    return
  
  def __repr__(self):
    return '%s(%s)' % (self.op, ','.join(map(repr, self.nodes)))


##  ListType
##
class ListType(SimpleTypeNode):

  ##  Element
  ##
  class Element(CompoundTypeNode):

    def __init__(self, elements):
      CompoundTypeNode.__init__(self)
      self.elements = elements
      for elem in self.elements:
        elem.connect(self)
      return

    def __repr__(self):
      return '|'.join(map(str, self.elements))

  class AppendMethod(SimpleTypeNode):

    def __init__(self, target):
      SimpleTypeNode.__init__(self)
      self.target = target
      return

    def __repr__(self):
      return '%r.append' % self.target

    def call(self, caller, args):
      args[0].connect(self.target.elem)
      return ConstFuncType(NoneType.get())

  #
  def __init__(self, elems):
    SimpleTypeNode.__init__(self)
    self.elem = self.Element(elems)
    return
  
  def __repr__(self):
    return '[%s]' % self.elem

  def desc1(self, done):
    return '[%s]' % self.elem.desc1(done)

  def get_element(self, subs, write=False):
    return self.elem

  def bind(self, obj):
    obj.connect(self.elem)
    return

  def get_iter(self):
    return self.elem

  def get_attr(self, name):
    if name == 'append':
      return self.AppendMethod(self)
    elif name == 'remove':
      return self.ListRemove(self)
    elif name == 'count':
      return self.ListCount(self)
    elif name == 'extend':
      return self.ListExtend(self)
    elif name == 'index':
      return self.ListIndex(self)
    elif name == 'pop':
      return self.ListPop(self)
    elif name == 'insert':
      return self.AppendMethod(self)
    elif name == 'remove':
      return self.AppendMethod(self)
    elif name == 'reverse':
      return ConstFuncType(NoneType.get())
    elif name == 'sort':
      return ConstFuncType(NoneType.get())
    raise NodeTypeError


##  TupleType
##
class TupleType(SimpleTypeNode):

  ##  ElementAll
  ##
  class ElementAll(CompoundTypeNode):

    def __init__(self, elements):
      CompoundTypeNode.__init__(self)
      self.elements = elements
      for elem in self.elements:
        elem.connect(self)
      return

    def __repr__(self):
      return '|'.join(map(str, self.elements))

  def __init__(self, elements):
    SimpleTypeNode.__init__(self)
    self.elements = elements
    self.elemall = self.ElementAll(elements)
    return
  
  def __repr__(self):
    return '(%s)' % ','.join(map(repr, self.elements))

  def desc1(self, done):
    return '(%s)' % ','.join( elem.desc1(done) for elem in self.elements )

  def get_nth(self, i):
    return self.elements[i]

  def get_element(self, subs, write=False):
    if write:
      raise NodeTypeError('cannot change tuple')
    return self.elemall

  def get_iter(self):
    return self.elemall


##  TupleUnpack
##
class TupleUnpack(CompoundTypeNode, ExceptionRaiser):

  ##  Element
  ##
  class Element(CompoundTypeNode):
    
    def __init__(self, tup, i):
      CompoundTypeNode.__init__(self)
      self.tup = tup
      self.i = i
      return
    
    def __repr__(self):
      return '<TupleElement: %r[%d]>' % (self.tup, self.i)

  def __init__(self, parent_frame, loc, tupobj, nelems):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.tupobj = tupobj
    self.elems = [ self.Element(self, i) for i in xrange(nelems) ]
    self.tupobj.connect(self, self.recv_tupobj)
    return

  def __repr__(self):
    return '<TupleUnpack: %r>' % (self.tupobj,)

  def get_element(self, i, write=False):
    return self.elems[i]

  def recv_tupobj(self, src):
    assert src is self.tupobj
    for obj in src.types:
      if isinstance(obj, TupleType):
        if len(obj.elements) != len(self.elems):
          self.raise_expt(ExceptionType(
            'ValueError',
            'tuple elements mismatch: len(%r) != %r' % (obj, len(self.elems))))
        else:
          for (i,elem) in enumerate(obj.elements):
            elem.connect(self.elems[i])
      if isinstance(obj, ListType):
        for elem in self.elems:
          obj.elem.connect(elem)
      else:
        self.raise_expt(ExceptionType(
          'TypeError',
          'not unpackable: %r' % src))
    return


##  DictType
##
class DictType(SimpleTypeNode):

  ##  Item
  class Item(CompoundTypeNode):

    def __init__(self, objs):
      CompoundTypeNode.__init__(self)
      for obj in objs:
        obj.connect(self)
      return

  def __init__(self, items):
    self.key = self.Item( k for (k,v) in items )
    self.value = self.Item( v for (k,v) in items )
    SimpleTypeNode.__init__(self)
    return
  
  def __repr__(self):
    return '{%s: %s}' % (self.key, self.value)

  def __eq__(self, obj):
    return (isinstance(obj, DictType) and
            self.key == obj.key and
            self.value == obj.value)
  def __hash__(self):
    return hash((self.key, self.value))

  def desc1(self, done):
    return '{%s: %s}' % (self.key.desc1(done), self.value.desc1(done))

  def bind(self, key, value):
    self.key.bind(key)
    self.value.bind(value)
    return

  def get_element(self, subs, write=False):
    assert len(subs) == 1
    if write:
      for k in subs:
        k.connect(self.key)
    return self.value

  def get_attr(self, name):
    if name == 'clear':
      return XXX
    elif name == 'copy':
      return XXX
    elif name == 'fromkeys':
      return XXX
    elif name == 'get':
      return XXX
    elif name == 'has_key':
      return XXX
    elif name == 'items':
      return XXX
    elif name == 'iteritems':
      return XXX
    elif name == 'iterkeys':
      return XXX
    elif name == 'itervalues':
      return XXX
    elif name == 'keys':
      return XXX
    elif name == 'pop':
      return XXX
    elif name == 'popitem':
      return XXX
    elif name == 'setdefault':
      return XXX
    elif name == 'update':
      return XXX
    elif name == 'values':
      return XXX
    raise NodeTypeError


##  SubRef
##
class SubRef(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, subs):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target = target
    self.objs = set()
    self.subs = subs
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return '%r[%s]' % (self.target, ':'.join(map(repr, self.subs)))

  def recv_target(self, src):
    self.objs.update(src.types)
    for obj in self.objs:
      try:
        obj.get_element(self.subs).connect(self)
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'TypeError',
          'unsubscriptable object: %r' % obj))
    return


##  SubAssign
##
class SubAssign(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target, subs, value):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target = target
    self.objs = set()
    self.subs = subs
    self.value = value
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'assign(%r%r, %r)' % (self.target, self.subs, self.value)

  def recv_target(self, src):
    self.objs.update(src.types)
    for obj in self.objs:
      try:
        self.value.connect(obj.get_element(self.subs, write=True))
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'TypeError',
          'unsubscriptable object: %r' % obj))
    return


##  GeneratorSlot
##
class GeneratorSlot(CompoundTypeNode):

  def __init__(self, value):
    CompoundTypeNode.__init__(self)
    self.types.add(self)
    self.value = value
    return


##  Generator
##
class Generator(SimpleTypeNode):

  def __init__(self, yields):
    SimpleTypeNode.__init__(self)
    self.elem = ListType.Element([ slot.value for slot in yields ])
    return

  def __repr__(self):
    return '(%s ...)' % self.elem

  def desc1(self, done):
    return '(%s ...)' % self.elem.desc1(done)

  def get_iter(self):
    return self.elem


##  IterRef
##
class IterRef(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, target):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent_frame, loc)
    self.target = target
    self.target.connect(self, self.recv_target)
    return

  def __repr__(self):
    return 'iter(%r)' % (self.target,)

  def recv_target(self, src):
    for obj in src.types:
      try:
        obj.get_iter().connect(self)
      except NodeTypeError:
        self.raise_expt(ExceptionType(
          'TypeError',
          '%r might not be an iterator: %r' % (self.target, obj)))
        continue
    return

    
##  ModuleType
##
class ModuleType(FuncType, ExceptionFrame):
  
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

  def __init__(self, reporter, tree, parent_space, name):
    FuncType.__init__(self, reporter, self, parent_space,
                      name, (), (), False, False, tree.node)
    ExceptionFrame.__init__(self)
    self.attrs = {}
    FunCall(self, tree, self, ())
    return
  
  def __repr__(self):
    return '<Module %s>' % self.name

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
      p(' %s = %s' % (k, v.describe()))
    self.body.show(p)
    return
  

##  Built-in Stuff
##

##  BuiltinType
##
class BuiltinType(SimpleTypeNode):

  NAME = None
  SINGLETON = None

  def __repr__(self):
    return '<%s>' % self.NAME

  @classmethod
  def get(klass):
    if not klass.SINGLETON:
      klass.SINGLETON = klass()
    return klass.SINGLETON

class NoneType(BuiltinType):
  NAME = 'NoneType'

class BoolType(BuiltinType):
  NAME = 'bool'

class NumberType(BuiltinType):
  NAME = 'number'
  rank = 0
class IntType(NumberType):
  NAME = 'int'
  rank = 1
class LongType(IntType):
  NAME = 'long'
  rank = 2
class FloatType(NumberType):
  NAME = 'float'
  rank = 3
class ComplexType(NumberType):
  NAME = 'complex'
  rank = 4

class BaseStringType(BuiltinType):
  NAME = 'basestring'
  def get_attr(self, name):
    if name == 'capitalize':
      return XXX
    elif name == 'center':
      return XXX
    elif name == 'count':
      return XXX
    elif name == 'decode':
      return XXX
    elif name == 'encode':
      return XXX
    elif name == 'endswith':
      return XXX
    elif name == 'expandtabs':
      return XXX
    elif name == 'find':
      return XXX
    elif name == 'index':
      return XXX
    elif name == 'isalnum':
      return XXX
    elif name == 'isalpha':
      return XXX
    elif name == 'isdigit':
      return XXX
    elif name == 'islower':
      return XXX
    elif name == 'isspace':
      return XXX
    elif name == 'istitle':
      return XXX
    elif name == 'isupper':
      return XXX
    elif name == 'join':
      return XXX
    elif name == 'ljust':
      return XXX
    elif name == 'lower':
      return XXX
    elif name == 'lstrip':
      return XXX
    elif name == 'partition':
      return XXX
    elif name == 'replace':
      return XXX
    elif name == 'rfind':
      return XXX
    elif name == 'rindex':
      return XXX
    elif name == 'rjust':
      return XXX
    elif name == 'rpartition':
      return XXX
    elif name == 'rsplit':
      return XXX
    elif name == 'rstrip':
      return XXX
    elif name == 'split':
      return XXX
    elif name == 'splitlines':
      return XXX
    elif name == 'startswith':
      return XXX
    elif name == 'strip':
      return XXX
    elif name == 'swapcase':
      return XXX
    elif name == 'title':
      return XXX
    elif name == 'translate':
      return XXX
    elif name == 'upper':
      return XXX
    elif name == 'zfill':
      return XXX
    raise NodeTypeError

class StrType(BaseStringType):
  NAME = 'str'
    
class UnicodeType(BaseStringType):
  NAME = 'unicode'
  def get_attr(self, name):
    if name == 'isdecimal':
      return XXX
    elif name == 'isnumeric':
      return XXX
    return BaseStringType.get_attr(self, name)


##  BuiltinModuleType
##
class BuiltinModuleType(ModuleType):

  def __init__(self, name):
    SimpleTypeNode.__init__(self)
    self.name = name
    self.attrs = {}
    return

  def get_attr(self, name):
    if name not in self.attrs:
      attr = ModuleType.Attr(name, self)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def __repr__(self):
    return '<BuiltinModule %s>' % self.name


##  BuiltinFuncType
##
class BuiltinFuncType(SimpleTypeNode):

  NAME = None

  class Body(CompoundTypeNode, ExceptionRaiser):
    
    def __init__(self, parent_frame):
      CompoundTypeNode.__init__(self)
      ExceptionRaiser.__init__(self, parent_frame)
      return
    
    def recv_basetype(self, types, src):
      for obj in src.types:
        if isinstance(obj, BuiltinType) and obj.typename in types:
          pass
        else:
          self.raise_expt(ExceptionType(
            'TypeError',
            'invalid type: %r (not %s)' % (obj, ','.join(types))))
      return

    def recv_int(self, src):
      return self.recv_basetype(('int','long'), src)
    def recv_str(self, src):
      return self.recv_basetype(('str','unicode'), src)
    def recv_xint(self, src):
      return self.recv_basetype(('int','long','float','bool'), src)

  def __repr__(self):
    return '<builtin %s>' % self.NAME


##  IntFunc
##
class IntFunc(BuiltinFuncType):

  NAME = 'int'

  ##  Body
  ##
  class Body(BuiltinFuncType.Body):
    
    def __init__(self, parent_frame, obj, base=None):
      BuiltinFuncType.Body.__init__(self, parent_frame)
      obj.connect(self)
      if base:
        base.connect(self, self.recv_xint)
      return
  
    def recv(self, src):
      for obj in src.types:
        if not isinstance(obj, BuiltinType):
          self.raise_expt(ExceptionType(
            'TypeError',
            'unsupported conversion: %s' % obj.typename))
          continue
        if obj.typename in ('int','long','float','bool'):
          continue
        if obj.typename in ('str','unicode','basestring'):
          self.raise_expt(ExceptionType(
            'ValueError',
            'might be conversion error'))
          continue
        if obj.typename in ('complex',):
          self.raise_expt(ExceptionType(
            'TypeError',
            'cannot convert complex'))
          continue
      return

  def call(self, caller, args):
    if not args:
      return IntType.get()
    if 2 < len(args):
      caller.raise_expt(ExceptionType(
        'TypeError',
        'too many argument: more than 2'))
    return self.Body(caller, *args)


##  StrFunc
##
class StrFunc(BuiltinFuncType):

  NAME = 'str'

  ##  Body
  ##
  class Body(BuiltinFuncType.Body):
    
    def __init__(self, parent_frame, obj):
      BuiltinFuncType.Body.__init__(self, parent_frame)
      self.types.add(StrType.get())
      self.obj = obj
      self.obj.connect(self)
      return
    
    def recv(self, src):
      for obj in src.types:
        if isinstance(obj, InstanceType):
          ClassType.OptionalAttr(obj, '__str__').call(self, ())
      return

  def call(self, caller, args):
    if not args:
      return StrType.get()
    if 1 < len(args):
      caller.raise_expt(ExceptionType(
        'TypeError',
        'too many argument: more than 1'))
    return self.Body(caller, *args)


##  RangeFunc
##
class RangeFunc(BuiltinFuncType):

  NAME = 'range'
  
  ##  Body
  ##
  class Body(BuiltinFuncType.Body):
    
    def __init__(self, parent_frame, loc, args):
      BuiltinFuncType.Body.__init__(self, parent_frame, loc)
      for arg in args:
        arg.connect(self, self.recv_int)
      XXX
      self.ListType([IntType.get()])
      return
  
  def call(self, caller, args):
    if not args or 3 < len(args):
      caller.raise_expt(ExceptionType(
        'TypeError',
        'invalid number of args: %d' % len(args)))
    return self.Body(caller, args)

  
##  BuiltinNamespace
##
class BuiltinNamespace(Namespace):

  def __init__(self):
    Namespace.__init__(self, None, '')
    self.register_var('True').bind(BoolType.get())
    self.register_var('False').bind(BoolType.get())
    self.register_var('None').bind(NoneType.get())
    self.register_var('__name__').bind(StrType.get())

    # int,float,bool,buffer,chr,dict,file,open,list,set,frozenset,
    # object,xrange,slice,type,unicode,tuple,super,str,staticmethod,classmethod,reversed
    self.register_var('int').bind(IntFunc())
    self.register_var('str').bind(StrFunc())

    # abs,all,any,apply,basestring,callable,chr,
    # cmp,coerce,compile,complex,delattr,dir,divmod,enumerate,eval,
    # execfile,filter,getattr,globals,hasattr,hash,
    # hex,id,input,intern,isinstance,issubclass,iter,len,locals,
    # long,map,max,min,oct,ord,pow,property,range,raw_input,
    # reduce,reload,repr,round,setattr,sorted,
    # sum,unichr,vars,xrange,zip
    self.register_var('range').bind(RangeFunc())
    
    return


##  Global stuff
##
BUILTIN_TYPE = dict(
  (cls.NAME, cls.get()) for cls in
  ( NoneType, BoolType, IntType, LongType, FloatType, StrType, UnicodeType )
  )
BUILTIN_NAMESPACE = BuiltinNamespace()

# find_module
class ModuleNotFound(Exception): pass
def find_module(name, paths):
  import os.path
  if debug:
    print >>stderr, 'find_module: name=%r' % name
  fname = name+'.py'
  for dirname in paths:
    path = os.path.join(dirname, name)
    if os.path.exists(path):
      return path
    path = os.path.join(dirname, fname)
    if os.path.exists(path):
      return path
  raise ModuleNotFound(name)

# load_module
def load_module(modname, asname=None, paths=['.']):
  def rec(n, parent):
    n._modname = modname
    for c in n.getChildNodes():
      rec(c, n)
    return
  path = find_module(modname, paths)
  name = asname or modname
  if debug:
    print >>stderr, 'load_module: %r' % path
  tree = parseFile(path)
  rec(tree, None)
  reporter = TreeReporter()
  return ModuleType(reporter, tree, BUILTIN_NAMESPACE, name)


##  build_assign(reporter, frame, namespace, node1, node2, evals)
##
def build_assign(reporter, frame, space, n, v, evals):
  if isinstance(n, ast.AssName) or isinstance(n, ast.Name):
    space[n.name].bind(v)
  elif isinstance(n, ast.AssTuple):
    tup = TupleUnpack(frame, n, v, len(n.nodes))
    for (i,c) in enumerate(n.nodes):
      build_assign(reporter, frame, space, c, tup.get_element(i), evals)
  elif isinstance(n, ast.AssAttr):
    obj = build_expr(reporter, frame, space, n.expr, evals)
    AttrAssign(n, obj, n.attrname, v)
  elif isinstance(n, ast.Subscript):
    obj = build_expr(reporter, frame, space, n.expr, evals)
    subs = [ build_expr(reporter, frame, space, expr, evals) for expr in n.subs ]
    SubAssign(frame, n, obj, subs, v)
  else:
    raise TypeError(n)
  return


##  build_expr(reporter, frame, namespace, tree, evals)
##
##  Constructs a TypeNode from a given syntax tree.
##
def build_expr(reporter, frame, space, tree, evals):

  if isinstance(tree, ast.Const):
    typename = type(tree.value).__name__
    expr = BUILTIN_TYPE[typename]

  elif isinstance(tree, ast.Name):
    try:
      expr = space[tree.name]
    except KeyError:
      frame.add_expt(tree, ExceptionType('NameError',
                                         'name %r is not defined' % tree.name))
      expr = UndefinedTypeNode(tree.name)

  elif isinstance(tree, ast.CallFunc):
    func = build_expr(reporter, frame, space, tree.node, evals)
    args = tuple( build_expr(reporter, frame, space, arg1, evals) for arg1 in tree.args )
    expr = FunCall(frame, tree, func, args)

  elif isinstance(tree, ast.Keyword):
    expr = KeywordArg(tree.name, build_expr(reporter, frame, space, tree.expr, evals))
    
  elif isinstance(tree, ast.Getattr):
    obj = build_expr(reporter, frame, space, tree.expr, evals)
    expr = AttrRef(frame, tree, obj, tree.attrname)

  elif isinstance(tree, ast.Subscript):
    obj = build_expr(reporter, frame, space, tree.expr, evals)
    subs = [ build_expr(reporter, frame, space, sub, evals) for sub in tree.subs ]
    expr = SubRef(frame, tree, obj, subs)

  elif isinstance(tree, ast.Slice):
    obj = build_expr(reporter, frame, space, tree.expr, evals)
    lower = upper = None
    if tree.lower:
      lower = build_expr(reporter, frame, space, tree.lower, evals)
    if tree.upper:
      upper = build_expr(reporter, frame, space, tree.upper, evals)
    expr = SliceRef(frame, tree, obj, lower, upper)

  elif isinstance(tree, ast.Tuple):
    elements = [ build_expr(reporter, frame, space, node, evals) for node in tree.nodes ]
    expr = TupleType(elements)

  elif isinstance(tree, ast.List):
    elems = [ build_expr(reporter, frame, space, node, evals) for node in tree.nodes ]
    expr = ListType(elems)

  elif isinstance(tree, ast.Dict):
    items = [ (build_expr(reporter, frame, space, k, evals),
               build_expr(reporter, frame, space, v, evals))
              for (k,v) in tree.items ]
    expr = DictType(items)

  # +, -, *, /, %, //, <<, >>, **, &, |, ^
  elif (isinstance(tree, ast.Add) or isinstance(tree, ast.Sub) or
        isinstance(tree, ast.Mul) or isinstance(tree, ast.Div) or
        isinstance(tree, ast.Mod) or isinstance(tree, ast.FloorDiv) or
        isinstance(tree, ast.LeftShift) or isinstance(tree, ast.RightShift) or
        isinstance(tree, ast.Power) or isinstance(tree, ast.Bitand) or
        isinstance(tree, ast.Bitor) or isinstance(tree, ast.Bitxor)):
    op = tree.__class__.__name__
    left = build_expr(reporter, frame, space, tree.left, evals)
    right = build_expr(reporter, frame, space, tree.right, evals)
    expr = BinaryOp(frame, tree, op, left, right)

  # ==, !=, <=, >=, <, >
  elif isinstance(tree, ast.Compare):
    expr0 = build_expr(reporter, frame, space, tree.expr, evals)
    comps = [ (op, build_expr(reporter, frame, space, node, evals)) for (op,node) in tree.ops ]
    expr = CompareOp(frame, tree, expr0, comps)

  # +,-
  elif (isinstance(tree, ast.UnaryAdd) or isinstance(tree, ast.UnarySub)):
    value = build_expr(reporter, frame, space, tree.expr, evals)
    expr = UnaryOp(frame, tree.__class__, value)

  # and, or
  elif (isinstance(tree, ast.And) or isinstance(tree, ast.Or)):
    nodes = [ build_expr(reporter, frame, space, node, evals) for node in tree.nodes ]
    expr = BooleanOp(tree.__class__.__name__, nodes)

  # not
  elif isinstance(tree, ast.Not):
    value = build_expr(reporter, frame, space, tree.expr, evals)
    expr = NotOp(frame, tree, value)

  # lambda
  elif isinstance(tree, ast.Lambda):
    defaults = [ build_expr(reporter, frame, space, value, evals) for value in tree.defaults ]
    expr = LambdaFuncType(reporter, frame, space, tree.argnames,
                          defaults, tree.varargs, tree.kwargs, tree.code)

  # list comprehension
  elif isinstance(tree, ast.ListComp):
    elems = [ build_expr(reporter, frame, space, tree.expr, evals) ]
    expr = ListType(elems)
    for qual in tree.quals:
      seq = build_expr(reporter, frame, space, qual.list, evals)
      build_assign(reporter, frame, space, qual.assign, IterRef(frame, qual.list, seq), evals)
      for qif in qual.ifs:
        build_expr(reporter, frame, space, qif.test, evals)

  # yield (for python 2.5)
  elif isinstance(tree, ast.Yield):
    value = build_expr(reporter, frame, space, tree.value, evals)
    expr = GeneratorSlot(value)
    evals.append(('y', expr)) # XXX ???

  else:
    raise SyntaxError(tree)

  assert isinstance(expr, TypeNode) or isinstance(expr, tuple), expr
  evals.append((None, expr))
  return expr


##  build_stmt
##
def build_stmt(reporter, frame, space, tree, evals, isfuncdef=False):
  assert isinstance(frame, ExceptionFrame)
  if 2 <= debug:
    print >>stderr, 'build: %r' % tree

  # def
  if isinstance(tree, ast.Function):
    name = tree.name
    defaults = [ build_expr(reporter, frame, space, value, evals) for value in tree.defaults ]
    func = FuncType(reporter, frame, space, name, tree.argnames,
                    defaults, tree.varargs, tree.kwargs, tree.code)
    if tree.decorators:
      for node in tree.decorators:
        decor = build_expr(reporter, frame, space, node, evals)
        func = FunCall(frame, tree, decor, [func])
    space[name].bind(func)

  # class
  elif isinstance(tree, ast.Class):
    name = tree.name
    bases = [ build_expr(reporter, frame, space, base, evals) for base in tree.bases ]
    klass = ClassType(reporter, frame, space, name, bases, tree.code, evals)
    space[name].bind(klass)

  # assign
  elif isinstance(tree, ast.Assign):
    for n in tree.nodes:
      value = build_expr(reporter, frame, space, tree.expr, evals)
      build_assign(reporter, frame, space, n, value, evals)

  # augassign
  elif isinstance(tree, ast.AugAssign):
    left = build_expr(reporter, frame, space, tree.node, evals)
    right = build_expr(reporter, frame, space, tree.expr, evals)
    value = AssignOp(frame, tree, tree.op, left, right)
    build_assign(reporter, frame, space, tree.node, value, evals)

  # return
  elif isinstance(tree, ast.Return):
    value = build_expr(reporter, frame, space, tree.value, evals)
    evals.append(('r', value))

  # yield (for python 2.4)
  elif isinstance(tree, ast.Yield):
    value = build_expr(reporter, frame, space, tree.value, evals)
    evals.append(('y', value))

  # (mutliple statements)
  elif isinstance(tree, ast.Stmt):
    stmt = None
    for stmt in tree.nodes:
      build_stmt(reporter, frame, space, stmt, evals)
    if isfuncdef:
      # if the last statement is not a Return
      if not isinstance(stmt, ast.Return):
        value = NoneType.get()
        evals.append(('r', value))

  # if, elif, else
  elif isinstance(tree, ast.If):
    for (expr,stmt) in tree.tests:
      value = build_expr(reporter, frame, space, expr, evals)
      build_stmt(reporter, frame, space, stmt, evals)
    if tree.else_:
      build_stmt(reporter, frame, space, tree.else_, evals)

  # for
  elif isinstance(tree, ast.For):
    seq = build_expr(reporter, frame, space, tree.list, evals)
    build_assign(reporter, frame, space, tree.assign, IterRef(frame, tree.list, seq), evals)
    build_stmt(reporter, frame, space, tree.body, evals)
    if tree.else_:
      build_stmt(reporter, frame, space, tree.else_, evals)

  # while
  elif isinstance(tree, ast.While):
    value = build_expr(reporter, frame, space, tree.test, evals)
    build_stmt(reporter, frame, space, tree.body, evals)
    if tree.else_:
      build_stmt(reporter, frame, space, tree.else_, evals)

  # try ... except
  elif isinstance(tree, ast.TryExcept):
    catcher = ExceptionCatcher(frame)
    for (expr,e,stmt) in tree.handlers:
      if expr:
        expts = build_expr(reporter, frame, space, expr, evals)
        v = catcher.add_handler(expts)
        if e:
          build_assign(reporter, frame, space, e, v, evals)
      else:
        catcher.add_all()
      build_stmt(reporter, frame, space, stmt, evals)
    build_stmt(reporter, catcher, space, tree.body, evals)
    if tree.else_:
      build_stmt(reporter, frame, space, tree.else_, evals)

  # try ... finally
  elif isinstance(tree, ast.TryFinally):
    build_stmt(reporter, frame, space, tree.body, evals)
    build_stmt(reporter, frame, space, tree.final, evals)

  # raise
  elif isinstance(tree, ast.Raise):
    # XXX ignoring tree.expr3 (what is this for anyway?)
    if tree.expr2:
      exctype = build_expr(reporter, frame, space, tree.expr1, evals)
      excarg = build_expr(reporter, frame, space, tree.expr2, evals)
      exc = ExptMaker(frame, tree.expr1, exctype, (excarg,))
    else:
      exctype = build_expr(reporter, frame, space, tree.expr1, evals)
      exc = ExptMaker(frame, tree.expr1, exctype, ())
    frame.add_expt(tree, exc)

  # printnl
  elif isinstance(tree, ast.Printnl):
    for node in tree.nodes:
      value = build_expr(reporter, frame, space, node, evals)

  # discard
  elif isinstance(tree, ast.Discard):
    value = build_expr(reporter, frame, space, tree.expr, evals)

  # pass
  elif isinstance(tree, ast.Pass):
    pass

  # import
  elif isinstance(tree, ast.Import):
    pass
  elif isinstance(tree, ast.From):
    pass
  # global
  elif isinstance(tree, ast.Global):
    pass

  # del
  elif isinstance(tree, ast.AssName):
    pass
  elif isinstance(tree, ast.AssTuple):
    pass
  elif isinstance(tree, ast.AssAttr):
    build_expr(reporter, frame, space, tree.expr, evals)
  elif isinstance(tree, ast.Subscript):
    build_expr(reporter, frame, space, tree.expr, evals)

  elif isinstance(tree, ast.Assert):
    if (isinstance(tree.test, ast.CallFunc) and
        isinstance(tree.test.node, ast.Name) and
        tree.test.node.name == 'isinstance'):
      (a,b) = tree.test.args
      tf = TypeFilter(frame, build_expr(reporter, frame, space, b, evals))
      build_expr(reporter, frame, space, a, evals).connect(tf)

  else:
    raise SyntaxError('unsupported syntax: %r' % tree)

  return



# main
def main(argv):
  global debug
  import getopt
  def usage():
    print 'usage: %s [-d] [file ...]' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'd')
  except getopt.GetoptError:
    return usage()
  for (k, v) in opts:
    if k == '-d': debug += 1
  for name in args:
    ExceptionRaiser.reset()
    module = load_module(name, '__main__')
    ExceptionRaiser.runall()
    module.showrec(stdout)
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
