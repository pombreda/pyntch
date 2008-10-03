#!/usr/bin/env python

# pros:
# evals.append...
# 

import sys, compiler
from compiler.ast import *
stdout = sys.stdout
stderr = sys.stderr
debug = 0


# TODO:
#  exceptions
#  builtin functions
#  sys, str method...
#  +=
#  list comprehension.
#  @classmethod, @staticmethod
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


##  Reporter
##
class Reporter:

  space = {}
  indlevel = 2

  @classmethod
  def put(klass, tree, t, s):
    while tree:
      if tree in klass.space:
        (_,msgs) = klass.space[tree]
        msgs.append((t,s))
        break
      tree = tree.parent
    return

  @classmethod
  def error(klass, tree, s):
    klass.put(tree, 'error', '%s(%s): %s' % (tree.modname, tree.lineno, s))
    return
  @classmethod
  def warn(klass, tree, s):
    klass.put(tree, 'warn', '%s(%s): %s' % (tree.modname, tree.lineno, s))
    return
  @classmethod
  def info(klass, tree, s):
    klass.put(tree, 'info', s)
    return
  
  @classmethod
  def register_tree(klass, tree, node):
    klass.put(tree, 'child', tree)
    klass.space[tree] = (node, [])
    return
  
  @classmethod
  def show(klass, tree, fp=sys.stdout, level=0):
    def indent(n): return ' '*(n*klass.indlevel)
    (node,msgs) = klass.space[tree]
    s = node.finish()
    fp.write('%s%s\n' % (indent(level), s))
    level += 1
    for (t,x) in msgs:
      if t == 'child':
        klass.show(x, fp=fp, level=level)
      else:
        fp.write('%s%s\n' % (indent(level), x))
    fp.write('\n')
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
    raise TypeError('SimpleTypeNode cannot receive a value.')

  def get_body(self, caller, args):
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

  def __init__(self):
    TypeNode.__init__(self, [self])
    return

  def __repr__(self):
    raise NotImplementedError, self.__class__

  def desc1(self, _):
    return repr(self)


class UndefinedTypeNode(TypeNode):
  
  def __init__(self):
    TypeNode.__init__(self, [])
    return
  
  def __repr__(self):
    return '(undef)'
  
  def desc1(self, _):
    return '(undef)'


##  CompoundTypeNode
##
class CompoundTypeNode(TypeNode):

  def __init__(self, *types):
    TypeNode.__init__(self, types)
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
    types = types.difference(self.types)
    self.types.update(types)
    if types:
      for (node,receiver) in self.sendto:
        (receiver or node.recv)(self)
    return


##  ExecutionNode
##
##  An execution node is a place where an exception belongs.
##
class ExecutionNode(object):

  def __init__(self):
    self.expts = set()
    self.callers = []
    return
  
  def propagate(self, node):
    assert isinstance(node, ExecutionNode), node
    if debug:
      print >>stderr, 'propagate: %r raises %s' % (node, ', '.join( obj.describe() for obj in self.expts ))
    self.callers.append(node)
    (node.recv_expt)(self)
    return

  def recv_expt(self, src):
    assert isinstance(src, ExecutionNode), src
    self.update_expts(src.expts)
    return

  def add_expt(self, exc):
    self.update_expts(set([exc]))
    return

  def update_expts(self, expts):
    expts = expts.difference(self.expts)
    self.expts.update(expts)
    if expts:
      for (node,receiver) in self.callers:
        (receiver or node.recv)(self)
    return


##  PrimitiveType
##
class PrimitiveType(SimpleTypeNode):
  
  def __init__(self, tree, realtype, rank=0):
    self.tree = tree
    self.realtype = realtype
    self.rank = rank
    self.typename = realtype.__name__
    SimpleTypeNode.__init__(self)
    return

  def __repr__(self):
    return '<PrimitiveType %s>' % self.typename

  def __eq__(self, obj):
    return isinstance(obj, PrimitiveType) and self.typename == obj.typename
  def __hash__(self):
    return hash(self.typename)

# built-in types
NONE_TYPE = PrimitiveType(None, type(None))
TYPE_TYPE = PrimitiveType(None, type)
BOOL_TYPE = PrimitiveType(None, bool)
INT_TYPE = PrimitiveType(None, int, 0)
LONG_TYPE = PrimitiveType(None, long, 1)
FLOAT_TYPE = PrimitiveType(None, float, 2)
STR_TYPE = PrimitiveType(None, str, 0)
UNICODE_TYPE = PrimitiveType(None, unicode, 1)
NUMBER_TYPE = ( INT_TYPE, LONG_TYPE, FLOAT_TYPE )
BASESTRING_TYPE = ( STR_TYPE, UNICODE_TYPE )

##  KeywordArg
##
class KeywordArg(SimpleTypeNode):

  def __init__(self, tree, name, value):
    SimpleTypeNode.__init__(self)
    self.tree = tree
    self.name = name
    self.value = value
    return

  def __repr__(self):
    return '%s=%r' % (self.name, self.value)


##  TypeFilter
##
class TypeFilter(CompoundTypeNode):
  
  def __init__(self, tree, *typeobjs):
    self.tree = tree
    self.typeobjs = typeobjs
    self.validtypes = set()
    CompoundTypeNode.__init__(self)
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
        Reporter.warn(self.tree, '%r not type in %r' % (obj, validtypes))
    self.update_types(types)
    return


##  ExceptionType
##
class ExceptionType(SimpleTypeNode):

  def __init__(self, tree, name, msg):
    SimpleTypeNode.__init__(self)
    self.tree = tree
    self.name = name
    self.msg = msg
    return

  def __repr__(self):
    return '<%s: %s at %s:%d>' % (self.name, self.msg, self.tree.modname, self.tree.lineno)

  def connect(self, node, receiver=None):
    if debug:
      print >>stderr, 'raise: %r :- %r' % (node, self)
    return

  def desc1(self, _):
    return repr(self)


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
    # def
    if isinstance(tree, Function):
      self.register_var(tree.name)
    # class
    elif isinstance(tree, Class):
      self.register_var(tree.name)
    # assign
    elif isinstance(tree, Assign):
      for c in tree.nodes:
        self.register_names(c)
    elif isinstance(tree, AugAssign):
      pass
    elif isinstance(tree, AssTuple):
      for c in tree.nodes:
        self.register_names(c)
    elif isinstance(tree, AssList):
      for c in tree.nodes:
        self.register_names(c)
    elif isinstance(tree, AssName):
      self.register_var(tree.name)
    elif isinstance(tree, AssAttr):
      pass
    elif isinstance(tree, Subscript):
      pass

    # (mutliple statements)
    elif isinstance(tree, Stmt):
      for stmt in tree.nodes:
        self.register_names(stmt)

    # if, elif, else
    elif isinstance(tree, If):
      for (_,stmt) in tree.tests:
        self.register_names(stmt)
      if tree.else_:
        self.register_names(tree.else_)

    # for
    elif isinstance(tree, For):
      self.register_names(tree.assign)
      self.register_names(tree.body)
      if tree.else_:
        self.register_names(tree.else_)

    # while
    elif isinstance(tree, While):
      self.register_names(tree.body)
      if tree.else_:
        self.register_names(tree.else_)

    # try ... except
    elif isinstance(tree, TryExcept):
      self.register_names(tree.body)
      for (_,e,stmt) in tree.handlers:
        if e:
          self.register_var(e.name)
        self.register_names(stmt)
      if tree.else_:
        self.register_names(tree.else_)

    # try ... finally
    elif isinstance(tree, TryFinally):
      self.register_names(tree.body)
      self.register_names(tree.final)

    # import
    elif isinstance(tree, Import):
      for (modname,name) in tree.names:
        asname = name or modname
        module = load_module(modname)
        self.register_var(asname)
        self[asname].bind(module)

    # from
    elif isinstance(tree, From):
      module = load_module(tree.modname)
      for (name0,name1) in tree.names:
        if name0 == '*':
          self.import_all(module.space)
        else:
          asname = name1 or name0
          self.register_var(asname)
          self[asname].bind(module)

    # other statements
    elif isinstance(tree, Discard):
      pass
    elif isinstance(tree, Return):
      pass
    elif isinstance(tree, Break):
      pass
    elif isinstance(tree, Continue):
      pass
    elif isinstance(tree, Raise):
      pass
    elif isinstance(tree, Assert):
      pass
    elif isinstance(tree, Printnl):
      pass
    elif isinstance(tree, Print):
      pass
    elif isinstance(tree, Yield):
      pass
    elif isinstance(tree, Exec):
      pass
    elif isinstance(tree, Pass):
      pass
    
    else:
      raise SyntaxError(tree)
    return

  def import_all(self, space):
    for (k,v) in space.vars.iteritems():
      self.vars[k] = v
    return


##  FuncType
##
class FuncType(SimpleTypeNode):
  
  def __init__(self, tree, parent_space, name, argnames, defaults, varargs, kwargs, code):
    SimpleTypeNode.__init__(self)
    Reporter.register_tree(tree, self)
    self.tree = tree
    self.name = name
    self.kwarg = self.vararg = None
    self.space = Namespace(parent_space, name)
    if kwargs:
      self.kwarg = argnames[-1]
      del argnames[-1]
      self.space.register_var(self.kwarg)
    if varargs:
      self.vararg = argnames[-1]
      del argnames[-1]
      self.space.register_var(self.vararg)
    self.argnames = tuple(argnames)
    maprec(lambda argname: self.space.register_var(argname), self.argnames)
    self.argvars = maprec(lambda argname: self.space[argname], self.argnames)
    self.defaults = tuple(defaults)
    def assign(var1, arg1):
      assert not isinstance(var1, list), var1
      assert not isinstance(arg1, list), arg1
      if isinstance(var1, tuple):
        tup = TupleUnpack(arg1.tree, arg1, len(var1))
        for (i,v) in enumerate(var1):
          assign(v, tup.get_element(i))
      else:
        arg1.connect(var1)
      return
    for (var1,arg1) in zip(self.argvars[-len(defaults):], self.defaults):
      assign(var1, arg1)
    self.callers = set()
    self.body = FuncBody(name)
    self.build_body(code)
    return

  def build_body(self, tree):
    evals = []
    self.space.register_names(tree)
    build_stmt(self.body, self.space, tree, evals, isfuncdef=True)
    self.body.set_retval(evals)
    return

  def __repr__(self):
    return ('<Function %s>' % (self.name))

  def get_body(self, caller, args):
    self.callers.add(caller)
    def assign(var1, arg1):
      assert not isinstance(var1, list), var1
      assert not isinstance(arg1, list), arg1
      if isinstance(arg1, KeywordArg):
        name = arg1.name
        if name not in self.space:
          Reporter.error(caller.tree, 'invalid argname: %r' % name)
        else:
          arg1.value.connect(self.space[name])
      elif isinstance(var1, tuple):
        tup = TupleUnpack(arg1.tree, arg1, len(var1))
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
          argvars = [ var1 for var1 in argvars if not isinstance(var1, Variable) or var1.name != name ]
        elif self.kwarg:
          kwargs.append(value)
        else:
          Reporter.error(caller.tree, 'invalid keyword argument: %r' % name)
      elif argvars:
        var1 = argvars.pop(0)
        assign(var1, arg1)
      elif self.vararg:
        varargs.append(arg1)
      else:
        Reporter.error(caller.tree, 'too many argument: more than %r' % (len(self.argvars)))
    if kwargs:
      self.space[self.kwarg].bind(DictType(self.tree, [ (STR_TYPE,obj) for obj in kwargs ]))
    if varargs:
      self.space[self.vararg].bind(TupleType(self.tree, tuple(varargs)))
    if argvars:
      Reporter.error(caller.tree, 'not enough argument: %r more' % (len(argvars)))
    return self.body

  def finish(self):
    for (k,v) in sorted(self.space):
      Reporter.info(self.tree, '%s = %s' % (k, v.describe()))
    Reporter.info(self.tree, 'return %s' % self.body.describe())
    for caller in self.callers:
      Reporter.info(self.tree, '# caller: %s(%s)' % (caller.tree.modname, caller.tree.lineno))
    r = list(recjoin(', ', self.argnames))
    if self.vararg:
      r.append('*'+self.vararg)
    if self.kwarg:
      r.append('**'+self.kwarg)
    return 'def %s(%s):' % (self.name, ', '.join(r))


##  LambdaFuncType
##
class LambdaFuncType(FuncType):
  
  def __init__(self, tree, parent_space, argnames, defaults, varargs, kwargs, code):
    name = '__lambda_%x' % id(tree)
    FuncType.__init__(self, tree, parent_space, name, argnames, defaults, varargs, kwargs, code)
    return

  def build_body(self, tree):
    evals = []
    evals.append(('r', build_expr(self.body, self.space, tree, evals)))
    self.body.set_retval(evals)
    return
  
  def __repr__(self):
    return ('<LambdaFunc %s>' % (self.name))


##  FuncBody
##
class FuncBody(CompoundTypeNode, ExecutionNode):

  def __init__(self, name):
    CompoundTypeNode.__init__(self)
    ExecutionNode.__init__(self)
    self.name = name
    return

  def set_retval(self, evals):
    returns = [ obj for (t,obj) in evals if t == 'r' ]
    yields = [ obj for (t,obj) in evals if t == 'y' ]
    assert returns
    if yields:
      retvals = [ Generator(tree, yields) ]
    else:
      retvals = returns
    for obj in retvals:
      obj.connect(self)
    return

  def __repr__(self):
    return '<FuncBody %s>' % self.name


##  FunCall
##
class FunCall(CompoundTypeNode):
  
  def __init__(self, execpath, tree, func, args):
    CompoundTypeNode.__init__(self)
    self.execpath = execpath
    self.tree = tree
    self.func = func
    self.args = args
    func.connect(self, self.recv_func)
    return

  def __repr__(self):
    return '<%r(%s)>' % (self.func, ','.join(map(repr, self.args)))

  def recv_func(self, src):
    for func in src.types:
      try:
        body = func.get_body(self, self.args)
      except NodeTypeError:
        Reporter.warn(self.tree, 'cannot call: %r might be %r' % (self.func, func))
        continue
      body.propagate(self.execpath)
      body.connect(self)
    return


##  ClassType
##
class ClassType(SimpleTypeNode):
  
  def __init__(self, tree, execpath, parent_space, name, bases, code, evals):
    SimpleTypeNode.__init__(self)
    Reporter.register_tree(tree, self)
    self.tree = tree
    self.name = name
    self.bases = bases
    self.space = Namespace(parent_space, name)
    self.attrs = {}
    if code:
      self.space.register_names(code)
      build_stmt(execpath, self.space, code, evals)
    self.instance = InstanceType(self)
    self.initbody = InitMethodBody(self.instance)
    return

  def __repr__(self):
    return ('<Class %s>' % (self.name,))

  def get_attr(self, name):
    if name not in self.attrs:
      attr = ClassAttr(name, self, self.bases)
      self.attrs[name] = attr
      try:
        self.space[name].connect(attr)
      except KeyError:
        pass
    else:
      attr = self.attrs[name]
    return attr

  def get_body(self, caller, args):
    self.initbody.bind_args(caller, args)
    return self.initbody
  
  def finish(self):
    for (_, attr) in sorted(self.attrs.iteritems()):
      Reporter.info(self.tree, 'class.%s = %s' % (attr.name, attr.describe()))
    for (_, attr) in sorted(self.instance.attrs.iteritems()):
      Reporter.info(self.tree, 'instance.%s = %s' % (attr.name, attr.describe()))
    return 'class %s:' % self.name


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
  
  # XXX check if defined at last.


##  InitMethodBody
##
class InitMethodBody(CompoundTypeNode):
  
  def __init__(self, instance):
    CompoundTypeNode.__init__(self, instance)
    self.binds = []
    self.instance = instance
    self.initmethod = instance.get_attr('__init__')
    self.initmethod.connect(self, self.recv_initmethod)
    return

  def __repr__(self):
    return '<InitMethod %r>' % self.initmethod

  def bind_args(self, caller, args):
    self.binds.append((caller, args))
    self.recv(self.initmethod)
    return

  def recv_initmethod(self, src):
    for func in src.types:
      for (caller,args) in self.binds:
        try:
          body = func.get_body(caller, args)
        except NodeTypeError:
          Reporter.warn(None, 'cannot call: %r might be %r' % (self.initmethod, func))
          continue
        body.connect(self)
    return

  def recv(self, _):
    # ignore return value
    return


##  InstanceType
##
class InstanceType(SimpleTypeNode):
  
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
      attr = InstanceAttr(name, self.klass, self)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def bind_func(self, func):
    if len(func.argnames) < 1:
      raise InvalidMethodError('no argument')
    if func not in self.boundfuncs:
      method = BoundMethodType(self, func)
      self.boundfuncs[func] = method
    else:
      method = self.boundfuncs[func]
    return method
      

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
        try:
          obj = self.instance.bind_func(obj)
          # XXX
          #elif isinstance(obj, ClassMethodType):
          #elif isinstance(obj, StaticMethodType):
        except InvalidMethodError:
          Reporter.warn(obj.tree, 'cannot call: %r no arg0' % (obj))
          continue
      types.add(obj)
    self.update(types)
    return


##  BoundMethodType
##
class BoundMethodType(SimpleTypeNode):
  
  def __init__(self, arg0, func):
    self.arg0 = arg0
    self.func = func
    assert 1 <= len(func.argnames)
    SimpleTypeNode.__init__(self)
    return
  
  def __repr__(self):
    return '<Bound %r(%s=%r)>' % (self.func, self.func.argnames[0], self.arg0)
  
  def __eq__(self, obj):
    return (isinstance(obj, BoundMethodType) and
            self.arg0 == obj.arg0 and
            self.func == obj.func)
  def __hash__(self):
    return hash((self.arg0, self.func))

  def get_body(self, caller, args):
    return self.func.get_body(caller, (self.arg0,)+tuple(args))


##  AttrRef
##
class AttrRef(CompoundTypeNode):
  
  def __init__(self, tree, target, attrname):
    CompoundTypeNode.__init__(self)
    self.tree = tree
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
        obj.get_attr(self.attrname).connect(self)
      except NodeTypeError:
        Reporter.warn(self.tree, 'cannot get attribute: %r might be %r, no attr %s' % (self.target, obj, self.attrname))
        continue
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
class BinaryOp(CompoundTypeNode):
  
  def __init__(self, tree, op, left, right):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.op = op
    self.lefttypes = set()
    self.righttypes = set()
    left.connect(self, self.recv_left)
    right.connect(self, self.recv_right)
    return
  
  def __repr__(self):
    return '%s(%r,%r)' % (self.op, self.lefttypes, self.righttypes)

  def recv_left(self, src):
    self.lefttypes.update(src.types)
    self.update()
    return
  def recv_right(self, src):
    self.righttypes.update(src.types)
    self.update()
    return

  VALID_TYPES = {
    (STR_TYPE, 'Mul', INT_TYPE): STR_TYPE,
    (UNICODE_TYPE, 'Mul', INT_TYPE): UNICODE_TYPE,
    }
  def update(self):
    for lobj in self.lefttypes:
      for robj in self.righttypes:
        if (lobj in NUMBER_TYPE) and (robj in NUMBER_TYPE):
          if self.op in ('Add','Sub','Mul','Div','Mod','FloorDiv'):
            if lobj.rank < robj.rank:
              self.update_types(set([robj]))
            else:
              self.update_types(set([lobj]))
            continue
        if lobj in BASESTRING_TYPE and robj in BASESTRING_TYPE and self.op == 'Add':
          if lobj.rank < robj.rank:
            self.update_types(set([robj]))
          else:
            self.update_types(set([lobj]))
          continue
        k = (lobj, self.op, robj)
        if k in self.VALID_TYPES:
          self.update_types(set([self.VALID_TYPES[k]]))
          continue
    return


##  CompareOp
##
class CompareOp(CompoundTypeNode):
  
  def __init__(self, tree, expr0, comps):
    CompoundTypeNode.__init__(self, BOOL_TYPE)
    self.tree = tree
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
  
  def __init__(self, tree, op, nodes):
    CompoundTypeNode.__init__(self, BOOL_TYPE)
    self.tree = tree
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
  
  def __init__(self, tree, elements):
    SimpleTypeNode.__init__(self)
    self.tree = tree
    self.elem = ListElement(elements)
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
      return ListAppend(self)
    elif name == 'remove':
      return ListRemove(self)
    elif name == 'count':
      return ListCount(self)
    elif name == 'extend':
      return ListExtend(self)
    elif name == 'index':
      return ListIndex(self)
    elif name == 'insert':
      return ListAppend(self)
    elif name == 'remove':
      return ListAppend(self)
    elif name == 'reverse':
      return NopFuncType()
    elif name == 'sort':
      return NopFuncType()
    raise NodeTypeError

class NopFuncType(SimpleTypeNode):
  def get_body(self, caller, args):
    return NONE_TYPE

class ListAppend(SimpleTypeNode):
  def __init__(self, target):
    SimpleTypeNode.__init__(self)
    self.target = target
    return

  def __repr__(self):
    return '%r.append' % self.target

  def get_body(self, caller, args):
    args[0].connect(self.target.elem)
    return NopFuncType()

class ListElement(CompoundTypeNode):
  
  def __init__(self, elements):
    CompoundTypeNode.__init__(self)
    self.elements = elements
    for elem in self.elements:
      elem.connect(self)
    return

  def __repr__(self):
    return '|'.join(map(str, self.elements))
  

##  TupleType
##
class TupleType(SimpleTypeNode):
  
  def __init__(self, tree, elements):
    SimpleTypeNode.__init__(self)
    self.tree = tree
    self.elements = elements
    self.elemall = TupleElementAll(elements)
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

class TupleElementAll(CompoundTypeNode):
  
  def __init__(self, elements):
    CompoundTypeNode.__init__(self)
    self.elements = elements
    for elem in self.elements:
      elem.connect(self)
    return

  def __repr__(self):
    return '|'.join(map(str, self.elements))

class TupleElement(CompoundTypeNode):
  def __init__(self, tup, i):
    CompoundTypeNode.__init__(self)
    self.tup = tup
    self.i = i
    return
  def __repr__(self):
    return '<TupleElement: %r[%d]>' % (self.tup, self.i)

class TupleUnpack(CompoundTypeNode):

  def __init__(self, tree, tupobj, nelems):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.tupobj = tupobj
    self.elems = [ TupleElement(self, i) for i in xrange(nelems) ]
    self.tupobj.connect(self, self.recv_tupobj)
    return

  def __repr__(self):
    return '<TupleUnpack: %r>' % (self.tupobj,)

  def get_element(self, i):
    return self.elems[i]

  def recv_tupobj(self, src):
    assert src is self.tupobj
    for obj in src.types:
      if isinstance(obj, TupleType):
        if len(obj.elements) != len(self.elems):
          Reporter.warn(self.tree, 'tuple elements mismatch: len(%r) != %r' %
                      (obj, len(self.elems)))
        else:
          for (i,elem) in enumerate(obj.elements):
            elem.connect(self.elems[i])
      else:
        Reporter.warn(self.tree, 'not tuple: %r' % src)
    return


##  DictType
##
class DictType(SimpleTypeNode):
  
  def __init__(self, tree, items):
    self.tree = tree
    self.key = DictItem( k for (k,v) in items )
    self.value = DictItem( v for (k,v) in items )
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

class DictItem(CompoundTypeNode):
  
  def __init__(self, objs):
    CompoundTypeNode.__init__(self)
    for obj in objs:
      obj.connect(self)
    return


##  SubRef
##
class SubRef(CompoundTypeNode):
  
  def __init__(self, tree, target, subs):
    CompoundTypeNode.__init__(self)
    self.tree = tree
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
      obj.get_element(self.subs).connect(self)
    return


##  SubAssign
##
class SubAssign(CompoundTypeNode):
  
  def __init__(self, tree, target, subs, value):
    CompoundTypeNode.__init__(self)
    self.tree = tree
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
      self.value.connect(obj.get_element(self.subs, write=True))
    return


##  GeneratorSlot
##
class GeneratorSlot(CompoundTypeNode):

  def __init__(self, tree, value):
    CompoundTypeNode.__init__(self, self)
    self.tree = tree
    self.value = value
    return

class Generator(SimpleTypeNode):

  def __init__(self, tree, yields):
    SimpleTypeNode.__init__(self)
    self.tree = tree
    self.elem = ListElement( slot.value for slot in yields )
    return

  def __repr__(self):
    return '(%s ...)' % self.elem

  def desc1(self, done):
    return '(%s ...)' % self.elem.desc1(done)

  def get_iter(self):
    return self.elem


##  IterRef
##
class IterRef(CompoundTypeNode):
  
  def __init__(self, tree, target):
    CompoundTypeNode.__init__(self)
    self.tree = tree
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
        Reporter.warn(self.tree, '%r might not be an iterator: %r' % (self.target, obj))
        continue
    return

    
##  ModuleType
##
class ModuleType(FuncType):
  
  def __init__(self, tree, parent_space, name):
    FuncType.__init__(self, tree, parent_space, name, (), (), False, False, tree.node)
    self.space.register_var('__name__').bind(STR_TYPE)
    self.attrs = {}
    #FunCall(tree, self, ())
    return
  
  def __repr__(self):
    return '<Module %s>' % self.name

  def get_attr(self, name):
    if name not in self.attrs:
      attr = ModuleAttr(name, self)
      self.attrs[name] = attr
      try:
        self.space[name].connect(attr)
      except KeyError:
        pass
    else:
      attr = self.attrs[name]
    return attr

  def finish(self):
    for (k,v) in sorted(self.space):
      Reporter.info(self.tree, '%s = %s' % (k, v.describe()))
    return '[%s]' % self.name
  

##  ModuleAttr
##
class ModuleAttr(CompoundTypeNode):
  
  def __init__(self, name, module):
    CompoundTypeNode.__init__(self)
    self.name = name
    self.module = module
    return

  def __repr__(self):
    return '%r.@%s' % (self.module, self.name)
  
  # XXX check if defined at last.


##  Built-in Stuff
##

##  BuiltinFuncType
##
class BuiltinFuncType(SimpleTypeNode):
  pass

class BuiltinTypeType(SimpleTypeNode):

  def __init__(self, typeobj):
    SimpleTypeNode.__init__(self)
    self.typeobj = typeobj
    return

  def __repr__(self):
    return '<BuiltinType: %r>' % self.typeobj

class BuiltinTypeCheck(CompoundTypeNode):

  def __init__(self, *validtypes):
    self.validtypes = set(validtypes)
    CompoundTypeNode.__init__(self)
    return

  def recv(self, src):
    for obj in src.types:
      if obj not in self.validtypes:
        Reporter.warn(obj.tree, '%r not type in %r' % (obj, self.validtypes))
      else:
        self.update_types(src.types)
    return

  def check(self, obj):
    obj.connect(self)
    return self



##  BuiltinNamespace
##
class BuiltinNamespace(Namespace):

  def __init__(self):
    Namespace.__init__(self, None, '')
    self.register_var('True').bind(BOOL_TYPE)
    self.register_var('False').bind(BOOL_TYPE)
    self.register_var('None').bind(NONE_TYPE)
    self.register_var('int').bind(BuiltinTypeType(INT_TYPE))
    #self.register_var('Exception').bind(BuiltinTypeType(EXC_TYPE))

    #self.register_var('abs').bind(BuiltinFuncType(BuiltinABSBody()))
    return

BUILTIN_NAMESPACE = BuiltinNamespace()

##  BuiltInModuleType
##
class BuiltinModuleType(ModuleType):

  def __init__(self, name):
    SimpleTypeNode.__init__(self)
    self.name = name
    self.attrs = {}
    return

  def get_attr(self, name):
    if name not in self.attrs:
      attr = ModuleAttr(name, self)
      self.attrs[name] = attr
    else:
      attr = self.attrs[name]
    return attr

  def __repr__(self):
    return '<BuiltinModule %s>' % self.name

BUILTIN_MODULE = {
  'sys': BuiltinModuleType('sys'),
}

# find_module
def find_module(name, paths):
  import os.path
  fname = name+'.py'
  for dirname in paths:
    path = os.path.join(dirname, name)
    if os.path.exists(path):
      return path
    path = os.path.join(dirname, fname)
    if os.path.exists(path):
      return path
  raise ImportError(name)

# load_module
def load_module(modname, asname=None, paths=['.']):
  if modname in BUILTIN_MODULE:
    return BUILTIN_MODULE[modname]
  def rec(n, parent):
    n.parent = parent
    n.modname = modname
    for c in n.getChildNodes():
      rec(c, n)
    return
  path = find_module(modname, paths)
  name = asname or modname
  tree = compiler.parseFile(path)
  rec(tree, None)
  return ModuleType(tree, BUILTIN_NAMESPACE, name)


# build_expr(execpath, namespace, tree, evals)
# Constructs a TypeNode from a given syntax tree.
def build_expr(execpath, space, tree, evals):

  if isinstance(tree, Const):
    expr = PrimitiveType(tree, type(tree.value))

  elif isinstance(tree, Name):
    try:
      expr = space[tree.name]
    except KeyError:
      expr = UndefinedTypeNode()
      execpath.add_expt(ExceptionType(tree, 'NameError', 'name %r is not defined' % tree.name))

  elif isinstance(tree, CallFunc):
    func = build_expr(execpath, space, tree.node, evals)
    args = tuple( build_expr(execpath, space, arg1, evals) for arg1 in tree.args )
    expr = FunCall(execpath, tree, func, args)

  elif isinstance(tree, Keyword):
    expr = KeywordArg(tree, tree.name, build_expr(execpath, space, tree.expr, evals))
    
  elif isinstance(tree, Getattr):
    obj = build_expr(execpath, space, tree.expr, evals)
    expr = AttrRef(tree, obj, tree.attrname)

  elif isinstance(tree, Subscript):
    obj = build_expr(execpath, space, tree.expr, evals)
    subs = [ build_expr(execpath, space, sub, evals) for sub in tree.subs ]
    expr = SubRef(tree, obj, subs)

  elif isinstance(tree, Slice):
    obj = build_expr(execpath, space, tree.expr, evals)
    lower = upper = None
    if tree.lower:
      lower = build_expr(execpath, space, tree.lower, evals)
    if tree.upper:
      upper = build_expr(execpath, space, tree.upper, evals)
    expr = SliceRef(tree, obj, lower, upper)

  elif isinstance(tree, Tuple):
    elements = [ build_expr(execpath, space, node, evals) for node in tree.nodes ]
    expr = TupleType(tree, elements)

  elif isinstance(tree, List):
    elements = [ build_expr(execpath, space, node, evals) for node in tree.nodes ]
    expr = ListType(tree, elements)

  elif isinstance(tree, Dict):
    items = [ (build_expr(execpath, space, k, evals), build_expr(execpath, space, v, evals))
              for (k,v) in tree.items ]
    expr = DictType(tree, items)

  # +, -, *, /, %, //, <<, >>, **, &, |, ^
  elif (isinstance(tree, Add) or isinstance(tree, Sub) or
        isinstance(tree, Mul) or isinstance(tree, Div) or
        isinstance(tree, Mod) or isinstance(tree, FloorDiv) or
        isinstance(tree, LeftShift) or isinstance(tree, RightShift) or
        isinstance(tree, Power) or isinstance(tree, Bitand) or
        isinstance(tree, Bitor) or isinstance(tree, Bitxor)):
    op = tree.__class__.__name__
    left = build_expr(execpath, space, tree.left, evals)
    right = build_expr(execpath, space, tree.right, evals)
    expr = BinaryOp(tree, op, left, right)

  # ==, !=, <=, >=, <, >
  elif isinstance(tree, Compare):
    expr0 = build_expr(execpath, space, tree.expr, evals)
    comps = [ (op, build_expr(execpath, space, node, evals)) for (op,node) in tree.ops ]
    expr = CompareOp(tree, expr0, comps)

  # +,-
  elif isinstance(tree, UnaryAdd) or isinstance(tree, UnarySub):
    value = build_expr(execpath, space, tree.expr, evals)
    expr = UnaryOp(tree.__class__, value)

  # and, or
  elif (isinstance(tree, And) or isinstance(tree, Or)):
    nodes = [ build_expr(execpath, space, node, evals) for node in tree.nodes ]
    expr = BooleanOp(tree, tree.__class__.__name__, nodes)

  # not
  elif isinstance(tree, Not):
    value = build_expr(execpath, space, tree.expr, evals)
    expr = NotOp(tree, value)

  # lambda
  elif isinstance(tree, Lambda):
    defaults = [ build_expr(execpath, space, value, evals) for value in tree.defaults ]
    expr = LambdaFuncType(tree, space, tree.argnames,
                          defaults, tree.varargs, tree.kwargs, tree.code)

  # yield (for python 2.5)
  elif isinstance(tree, Yield):
    value = build_expr(execpath, space, tree.value, evals)
    expr = GeneratorSlot(tree, value)
    evals.append(('y', expr)) # XXX

  else:
    raise SyntaxError(tree)

  assert isinstance(expr, TypeNode) or isinstance(expr, tuple), expr
  evals.append((None, expr))
  return expr


# build_stmt
def build_stmt(execpath, space, tree, evals, isfuncdef=False):
  assert isinstance(execpath, ExecutionNode)
  if 2 <= debug:
    print >>stderr, 'build: %r' % tree

  def assign(n, v):
    if isinstance(n, AssName):
      space[n.name].bind(v)
    elif isinstance(n, AssTuple):
      tup = TupleUnpack(n, v, len(n.nodes))
      for (i,c) in enumerate(n.nodes):
        assign(c, tup.get_element(i))
    elif isinstance(n, AssAttr):
      obj = build_expr(execpath, space, n.expr, evals)
      AttrAssign(n, obj, n.attrname, v)
    elif isinstance(n, Subscript):
      obj = build_expr(execpath, space, n.expr, evals)
      subs = [ build_expr(execpath, space, expr, evals) for expr in n.subs ]
      evals.extend( (False, sub) for sub in subs )
      SubAssign(n, obj, subs, v)
    else:
      raise TypeError(n)
    return

  # def
  if isinstance(tree, Function):
    name = tree.name
    defaults = [ build_expr(execpath, space, value, evals) for value in tree.defaults ]
    func = FuncType(tree, space, name, tree.argnames,
                    defaults, tree.varargs, tree.kwargs, tree.code)
    space[name].bind(func)

  # class
  elif isinstance(tree, Class):
    name = tree.name
    bases = [ build_expr(execpath, space, base, evals) for base in tree.bases ]
    klass = ClassType(tree, execpath, space, name, bases, tree.code, evals)
    space[name].bind(klass)

  # assign
  elif isinstance(tree, Assign):
    for n in tree.nodes:
      value = build_expr(execpath, space, tree.expr, evals)
      assign(n, value)

  # return
  elif isinstance(tree, Return):
    value = build_expr(execpath, space, tree.value, evals)
    evals.append(('r', value))

  # yield (for python 2.4)
  elif isinstance(tree, Yield):
    value = build_expr(execpath, space, tree.value, evals)
    evals.append(('y', value)) # XXX

  # (mutliple statements)
  elif isinstance(tree, Stmt):
    stmt = None
    for stmt in tree.nodes:
      build_stmt(execpath, space, stmt, evals)
    if isfuncdef:
      # if the last statement is not a Return
      if not isinstance(stmt, Return):
        value = NONE_TYPE
        evals.append(('r', value))

  # if, elif, else
  elif isinstance(tree, If):
    for (expr,stmt) in tree.tests:
      value = build_expr(execpath, space, expr, evals)
      build_stmt(execpath, space, stmt, evals)
    if tree.else_:
      build_stmt(execpath, space, tree.else_, evals)

  # for
  elif isinstance(tree, For):
    seq = build_expr(execpath, space, tree.list, evals)
    assign(tree.assign, IterRef(tree.list, seq))
    build_stmt(execpath, space, tree.body, evals)
    if tree.else_:
      build_stmt(execpath, space, tree.else_, evals)

  # while
  elif isinstance(tree, While):
    value = build_expr(execpath, space, tree.test, evals)
    build_stmt(execpath, space, tree.body, evals)
    if tree.else_:
      build_stmt(execpath, space, tree.else_, evals)

  # try ... except
  elif isinstance(tree, TryExcept):
    build_stmt(execpath, space, tree.body, evals)
    #XXX exceptions.update(__)
    for (exc,e,stmt) in tree.handlers:
      value = build_expr(execpath, space, exc, evals)
      assign(e, value)
      build_stmt(execpath, space, stmt, evals)
    if tree.else_:
      build_stmt(execpath, space, tree.else_, evals)

  # try ... finally
  elif isinstance(tree, TryFinally):
    build_stmt(execpath, space, tree.body, evals)
    build_stmt(execpath, space, tree.final, evals)

  # raise
  elif isinstance(tree, Raise):
    if tree.expr2:
      exctype = build_expr(execpath, space, tree.expr1, evals)
      excarg = build_expr(execpath, space, tree.expr2, evals)
      exc = exctype # XXX
    else:
      value = build_expr(execpath, space, tree.expr1, evals)
      exc = value # XXX
    execpath.add_expt(exc)

  # printnl
  elif isinstance(tree, Printnl):
    for node in tree.nodes:
      value = build_expr(execpath, space, node, evals)

  # discard
  elif isinstance(tree, Discard):
    value = build_expr(execpath, space, tree.expr, evals)

  # pass
  elif isinstance(tree, Pass):
    pass

  # import
  elif isinstance(tree, Import):
    pass
  elif isinstance(tree, From):
    pass

  # del
  elif isinstance(tree, AssName):
    pass
  elif isinstance(tree, AssTuple):
    pass
  elif isinstance(tree, AssAttr):
    build_expr(execpath, space, tree.expr, evals)
  elif isinstance(tree, Subscript):
    build_expr(execpath, space, tree.expr, evals)

  elif isinstance(tree, Assert):
    if (isinstance(tree.test, CallFunc) and
        isinstance(tree.test.node, Name) and
        tree.test.node.name == 'isinstance'):
      (a,b) = tree.test.args
      build_expr(execpath, space, a, evals).connect(TypeFilter(a, build_expr(execpath, space, b, evals)))

  else:
    raise SyntaxError(tree)

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
    module = load_module(name, '__main__')
    Reporter.show(module.tree)
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
