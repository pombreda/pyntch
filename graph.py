#!/usr/bin/env python
import sys, compiler
from compiler.ast import *
stdout = sys.stdout
stderr = sys.stderr
debug = 0

# TODO:
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

def recjoin(k, seq):
  for x in seq:
    if isinstance(x, tuple):
      yield '(%s)' % k.join(recjoin(k, x))
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

class TypeNode:

  def __init__(self, *types):
    self.types = set(types)
    self.sendto = set()
    return

  def connect(self, node):
    assert isinstance(node, CompoundTypeNode), node
    if node in self.sendto: return
    if debug:
      print >>stderr, 'connect: %r :- %r' % (node,self)
    assert node not in self.sendto
    self.sendto.add(node)
    node.recv(self)
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
    TypeNode.__init__(self, self)
    return

  def __repr__(self):
    raise NotImplementedError, self.__class__

  def desc1(self, _):
    return repr(self)

  
##  CompoundTypeNode
##
class CompoundTypeNode(TypeNode):

  def desc1(self, done):
    if self in done:
      return '...'
    else:
      done.add(self)
      return '{%s}' % '|'.join( obj.desc1(done) for obj in self.types )

  def recv(self, src):
    self.update(src.types)
    return

  def update(self, types):
    diff = types.difference(self.types)
    if diff:
      self.types.update(diff)
      for node in list(self.sendto):
        node.recv(self)
    return


##  UndefinedType
##
class UndefinedType(TypeNode):

  def __repr__(self):
    return '<undef>'

  def describe(self):
    return 'undef'

  def recv(self, src):
    return


##  PrimitiveType
##
class PrimitiveType(SimpleTypeNode):
  
  def __init__(self, tree, typeobj):
    self.typename = type(typeobj).__name__
    self.tree = tree
    SimpleTypeNode.__init__(self)
    return

  def __repr__(self):
    return '<%s>' % self.typename

  def __eq__(self, obj):
    return isinstance(obj, PrimitiveType) and self.typename == obj.typename
  def __hash__(self):
    return hash(self.typename)

# None
NONE_TYPE = PrimitiveType(None, None)
BOOL_TYPE = PrimitiveType(None, True)
INT_TYPE = PrimitiveType(None, 1)
LONG_TYPE = PrimitiveType(None, 1L)
FLOAT_TYPE = PrimitiveType(None, 1.0)
STR_TYPE = PrimitiveType(None, '')
UNICODE_TYPE = PrimitiveType(None, u'')

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
  
  def __init__(self, tree, *objs):
    self.tree = tree
    self.objs = objs
    self.validtypes = set()
    CompoundTypeNode.__init__(self)
    for obj in objs:
      obj.connect(self)
    return

  def __repr__(self):
    return ('<TypeFilter: %s: %s>' % 
            (','.join(map(repr, self.objs)),
             '|'.join(map(repr, self.validtypes))))
  
  def recv(self, src):
    if src in self.objs:
      self.validtypes.update(src.types)
    else:
      types = set()
      for obj in src.types:
        if obj in self.validtypes:
          types.add(obj)
        else:
          Reporter.warn(self.tree, '%r not type in %r' % (obj, self.validtypes))
      self.update(types)
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

  def __init__(self, parent, name):
    self.parent = parent
    self.name = name
    self.vars = {}
    self.msgs = []
    if parent:
      self.name = parent.name+'.'+name
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
      self = self.parent
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


##  GlobalNamespace
##
class GlobalNamespace(Namespace):
  def __init__(self):
    Namespace.__init__(self, None, '')
    self.register_var('True').bind(BOOL_TYPE)
    self.register_var('False').bind(BOOL_TYPE)
    self.register_var('None').bind(NONE_TYPE)
    self.register_var('int').bind(INT_TYPE)
    self.register_var('long').bind(LONG_TYPE)
    self.register_var('float').bind(FLOAT_TYPE)
    self.register_var('str').bind(STR_TYPE)
    self.register_var('unicode').bind(UNICODE_TYPE)
    return

GLOBAL_NAMESPACE = GlobalNamespace()


##  BuiltinNamespace
##
class BuiltinNamespace(Namespace):
  
  def __init__(self, name):
    Namespace.__init__(self, GLOBAL_NAMESPACE, name)
    return


# build_expr
def build_expr(space, tree, evals):

  if isinstance(tree, Const):
    expr = PrimitiveType(tree, tree.value)

  elif isinstance(tree, Name):
    try:
      expr = space[tree.name]
    except KeyError:
      Reporter.error(tree, 'undefined variable: %r' % tree.name)
      expr = UndefinedType()

  elif isinstance(tree, CallFunc):
    func = build_expr(space, tree.node, evals)
    args = tuple( build_expr(space, arg1, evals) for arg1 in tree.args )
    expr = FunCall(tree, func, args)

  elif isinstance(tree, Keyword):
    expr = KeywordArg(tree, tree.name, build_expr(space, tree.expr, evals))
    
  elif isinstance(tree, Getattr):
    obj = build_expr(space, tree.expr, evals)
    expr = AttrRef(tree, obj, tree.attrname)

  elif isinstance(tree, Subscript):
    obj = build_expr(space, tree.expr, evals)
    subs = [ build_expr(space, sub, evals) for sub in tree.subs ]
    expr = SubRef(tree, obj, subs)

  elif isinstance(tree, Slice):
    obj = build_expr(space, tree.expr, evals)
    lower = upper = None
    if tree.lower:
      lower = build_expr(space, tree.lower, evals)
    if tree.upper:
      upper = build_expr(space, tree.upper, evals)
    expr = SliceRef(tree, obj, lower, upper)

  elif isinstance(tree, Tuple):
    elements = [ build_expr(space, node, evals) for node in tree.nodes ]
    expr = TupleType(tree, elements)

  elif isinstance(tree, List):
    elements = [ build_expr(space, node, evals) for node in tree.nodes ]
    expr = ListType(tree, elements)

  elif isinstance(tree, Dict):
    items = [ (build_expr(space, k, evals), build_expr(space, v, evals))
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
    left = build_expr(space, tree.left, evals)
    right = build_expr(space, tree.right, evals)
    expr = BinaryOp(tree, op, left, right)

  # ==, !=, <=, >=, <, >
  elif isinstance(tree, Compare):
    expr0 = build_expr(space, tree.expr, evals)
    comps = [ (op, build_expr(space, node, evals)) for (op,node) in tree.ops ]
    expr = CompareOp(tree, expr0, comps)

  # +,-
  elif isinstance(tree, UnaryAdd) or isinstance(tree, UnarySub):
    value = build_expr(space, tree.expr, evals)
    expr = UnaryOp(tree.__class__, value)

  # and, or
  elif (isinstance(tree, And) or isinstance(tree, Or)):
    nodes = [ build_expr(space, node, evals) for node in tree.nodes ]
    expr = BooleanOp(tree, tree.__class__.__name__, nodes)

  # not
  elif isinstance(tree, Not):
    value = build_expr(space, tree.expr, evals)
    expr = NotOp(tree, value)

  # lambda
  elif isinstance(tree, Lambda):
    defaults = [ build_expr(space, value, evals) for value in tree.defaults ]
    expr = LambdaFuncType(tree, space, tree.argnames,
                          defaults, tree.varargs, tree.kwargs)
    expr.set_code(tree.code)

  # yield (for python 2.5)
  elif isinstance(tree, Yield):
    value = build_expr(space, tree.value, evals)
    expr = GeneratorSlot(tree, value)
    evals.append((2, expr)) # XXX

  else:
    raise SyntaxError(tree)

  assert isinstance(expr, TypeNode) or isinstance(expr, tuple)
  return expr


# build_stmt
def build_stmt(space, tree, evals, isfuncdef=False):

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
      obj = build_expr(space, n.expr, evals)
      evals.append((0, obj))
      AttrAssign(n, obj, n.attrname, v)
    elif isinstance(n, Subscript):
      obj = build_expr(space, n.expr, evals)
      evals.append((0, obj))
      subs = [ build_expr(space, expr, evals) for expr in n.subs ]
      evals.extend( (False, sub) for sub in subs )
      SubAssign(n, obj, subs, v)
    else:
      raise TypeError(n)
    return

  # def
  if isinstance(tree, Function):
    name = tree.name
    defaults = [ build_expr(space, value, evals) for value in tree.defaults ]
    func = FuncType(tree, space, name, tree.argnames,
                    defaults, tree.varargs, tree.kwargs)
    func.set_code(tree.code)
    space[name].bind(func)

  # class
  elif isinstance(tree, Class):
    name = tree.name
    bases = [ build_expr(space, base, evals) for base in tree.bases ]
    klass = ClassType(tree, space, name, bases, tree.code, evals)
    space[name].bind(klass)

  # assign
  elif isinstance(tree, Assign):
    for n in tree.nodes:
      value = build_expr(space, tree.expr, evals)
      evals.append((0, value))
      assign(n, value)

  # return
  elif isinstance(tree, Return):
    value = build_expr(space, tree.value, evals)
    evals.append((1, value))

  # yield (for python 2.4)
  elif isinstance(tree, Yield):
    value = build_expr(space, tree.value, evals)
    evals.append((2, value)) # XXX

  # (mutliple statements)
  elif isinstance(tree, Stmt):
    stmt = None
    for stmt in tree.nodes:
      build_stmt(space, stmt, evals)
    if isfuncdef:
      # if the last statement is not a Return
      if not isinstance(stmt, Return):
        value = PrimitiveType(None, None)
        evals.append((1, value))

  # if, elif, else
  elif isinstance(tree, If):
    for (expr,stmt) in tree.tests:
      value = build_expr(space, expr, evals)
      evals.append((0, value))
      build_stmt(space, stmt, evals)
    if tree.else_:
      build_stmt(space, tree.else_, evals)

  # for
  elif isinstance(tree, For):
    seq = build_expr(space, tree.list, evals)
    evals.append((0, seq))
    assign(tree.assign, IterRef(tree.list, seq))
    build_stmt(space, tree.body, evals)
    if tree.else_:
      build_stmt(space, tree.else_, evals)

  # while
  elif isinstance(tree, While):
    value = build_expr(space, tree.test, evals)
    evals.append((0, value))
    build_stmt(space, tree.body, evals)
    if tree.else_:
      build_stmt(space, tree.else_, evals)

  # try ... except
  elif isinstance(tree, TryExcept):
    build_stmt(space, tree.body, evals)
    #XXX exceptions.update(__)
    for (exc,e,stmt) in tree.handlers:
      value = build_expr(space, exc, evals)
      evals.append((0, value))
      assign(e, value)
      build_stmt(space, stmt, evals)
    if tree.else_:
      build_stmt(space, tree.else_, evals)

  # try ... finally
  elif isinstance(tree, TryFinally):
    build_stmt(space, tree.body, evals)
    build_stmt(space, tree.final, evals)

  # printnl
  elif isinstance(tree, Printnl):
    for node in tree.nodes:
      value = build_expr(space, node, evals)
      evals.append((0, value))

  # discard
  elif isinstance(tree, Discard):
    value = build_expr(space, tree.expr, evals)
    evals.append((0, value))

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
    evals.append((0, build_expr(space, tree.expr, evals)))
  elif isinstance(tree, Subscript):
    evals.append((0, build_expr(space, tree.expr, evals)))

  elif isinstance(tree, Assert):
    if (isinstance(tree.test, CallFunc) and
        isinstance(tree.test.node, Name) and
        tree.test.node.name == 'isinstance'):
      (a,b) = tree.test.args
      build_expr(space, a, evals).connect(TypeFilter(a, build_expr(space, b, evals)))

  else:
    raise SyntaxError(tree)

  return


##  FuncType
##
class BuiltinFuncType(SimpleTypeNode):

  def __init__(self, name, retval):
    self.name = name
    self.retval = retval
    return

  def __repr__(self):
    return ('<BuiltInFunction %s>' % (self.name))

  def get_body(self, caller, args):
    return self.retval


class FuncType(SimpleTypeNode):
  
  def __init__(self, tree, parent, name, argnames, defaults, varargs, kwargs):
    SimpleTypeNode.__init__(self)
    self.tree = tree
    self.parent = parent
    self.name = name
    self.kwarg = self.vararg = None
    self.space = Namespace(parent, name)
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
    self.evals = []
    self.callers = set()
    Reporter.register_tree(tree, self)
    return

  def __repr__(self):
    return ('<Function %s>' % (self.name))

  def set_code(self, code):
    self.space.register_names(code)
    build_stmt(self.space, code, self.evals, isfuncdef=True)
    self.body = FuncBody(self)
    return

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
      Reporter.info(self.tree, '%r' % caller)
    r = list(recjoin(', ', self.argnames))
    if self.vararg:
      r.append('*'+self.vararg)
    if self.kwarg:
      r.append('**'+self.kwarg)
    return 'def %s(%s):' % (self.name, ', '.join(r))


##  LambdaFuncType
##
class LambdaFuncType(FuncType):
  
  def __init__(self, tree, parent, argnames, defaults, varargs, kwargs):
    name = '__lambda_%x' % id(tree)
    FuncType.__init__(self, tree, parent, name, argnames, defaults, varargs, kwargs)
    return
  
  def __repr__(self):
    return ('<LambdaFunc %s>' % (self.name))

  def set_code(self, code):
    self.evals.append((1, build_expr(self.space, code)))
    self.body = FuncBody(self)
    return


##  FuncBody
##
class FuncBody(CompoundTypeNode):

  def __init__(self, func):
    CompoundTypeNode.__init__(self)
    self.func = func
    evals = [ obj for (t,obj) in func.evals if t == 0 ]
    returns = [ obj for (t,obj) in func.evals if t == 1 ]
    yields = [ obj for (t,obj) in func.evals if t == 2 ]
    assert returns
    if yields:
      self.retvals = [ Generator(func.tree, yields) ]
    else:
      self.retvals = returns
    for obj in (evals+self.retvals):
      obj.connect(self)
    return

  def __repr__(self):
    return '<FuncBody %r>' % self.func
  
  def recv(self, src):
    if src in self.retvals:
      self.update(src.types)
    return


##  FunCall
##
class FunCall(CompoundTypeNode):
  
  def __init__(self, tree, func, args):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.func = func
    self.args = args
    func.connect(self)
    return

  def __repr__(self):
    return '<%r(%s)>' % (self.func, ','.join(map(repr, self.args)))

  def recv(self, src):
    if src is self.func:
      for func in src.types:
        try:
          body = func.get_body(self, self.args)
        except NodeTypeError:
          Reporter.warn(self.tree, 'cannot call: %r might be %r' % (self.func, func))
          continue
        body.connect(self)
    else:
      self.update(src.types)
    return


##  ClassType
##
class ClassType(SimpleTypeNode):
  
  def __init__(self, tree, parent, name, bases, code=None, evals=None):
    SimpleTypeNode.__init__(self)
    self.tree = tree
    self.parent = parent
    self.name = name
    self.bases = bases
    self.space = Namespace(parent, name)
    self.attrs = {}
    if code:
      self.space.register_names(code)
      build_stmt(self.space, code, evals)
    self.instance = InstanceType(self)
    self.initbody = InitMethodBody(self.instance)
    Reporter.register_tree(tree, self)
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
      base.connect(self)
    return

  def __repr__(self):
    return '%r.@%s' % (self.klass, self.name)
  
  def recv(self, src):
    if src in self.bases:
      for obj in src.types:
        obj.get_attr(self.name).connect(self)
    else:
      self.update(src.types)
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
    self.initmethod.connect(self)
    return

  def __repr__(self):
    return '<InitMethod %r>' % self.initmethod

  def bind_args(self, caller, args):
    self.binds.append((caller, args))
    self.recv(self.initmethod)
    return

  def recv(self, src):
    if src is self.initmethod:
      for func in src.types:
        for (caller,args) in self.binds:
          try:
            body = func.get_body(caller, args)
          except NodeTypeError:
            Reporter.warn(None, 'cannot call: %r might be %r' % (self.initmethod, func))
            continue
          body.connect(self)
    else:
      # ignore return value
      pass
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
    klass.connect(self)
    return

  def __repr__(self):
    return '%r.@%s' % (self.instance, self.name)
  
  def recv(self, src):
    if src == self.klass:
      for obj in src.types:
        obj.get_attr(self.name).connect(self)
    else:
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
  
  def __init__(self, tree, refobj, attrname):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.refobj = refobj
    self.attrname = attrname
    self.objs = set()
    self.refobj.connect(self)
    return

  def __repr__(self):
    return '%r.%s' % (self.refobj, self.attrname)

  def recv(self, src):
    if src == self.refobj:
      self.objs.update(src.types)
      for obj in self.objs:
        try:
          obj.get_attr(self.attrname).connect(self)
        except NodeTypeError:
          Reporter.warn(self.tree, 'cannot get attribute: %r might be %r, no attr %s' % (self.refobj, obj, self.attrname))
          continue
    else:
      self.update(src.types)
    return


##  AttrAssign
##
class AttrAssign(CompoundTypeNode):
  
  def __init__(self, tree, refobj, attrname, value):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.refobj = refobj
    self.objs = set()
    self.attrname = attrname
    self.value = value
    self.refobj.connect(self)
    return

  def __repr__(self):
    return 'assign(%r.%s, %r)' % (self.refobj, self.attrname, self.value)

  def recv(self, src):
    assert src is self.refobj
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
    self.left = left
    self.right = right
    self.left.connect(self)
    self.right.connect(self)
    return
  
  def __repr__(self):
    return '%s(%r,%r)' % (self.op, self.left, self.right)


##  CompareOp
##
class CompareOp(CompoundTypeNode):
  
  def __init__(self, tree, expr0, comps):
    CompoundTypeNode.__init__(self, PrimitiveType(None, False))
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
    CompoundTypeNode.__init__(self, PrimitiveType(None, False))
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
    elif name == 'remove':
      return NopFuncType()
    elif name == 'sort':
      return NopFuncType()
    raise NodeTypeError

class NopFuncType(SimpleTypeNode):
  def get_body(self, caller, args):
    return NONE_TYPE

class ListAppend(SimpleTypeNode):
  def __init__(self, refobj):
    SimpleTypeNode.__init__(self)
    self.refobj = refobj
    return

  def __repr__(self):
    return '%r.append' % self.refobj

  def get_body(self, caller, args):
    args[0].connect(self.refobj.elem)
    return self.refobj.elem

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

  def __init__(self, tree, refobj, nelems):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.refobj = refobj
    self.elems = [ TupleElement(self, i) for i in xrange(nelems) ]
    self.refobj.connect(self)
    return

  def __repr__(self):
    return '<TupleUnpack: %r>' % (self.refobj,)

  def get_element(self, i):
    return self.elems[i]

  def recv(self, src):
    assert src is self.refobj
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
    self.objs = set()
    for obj in objs:
      self.bind(obj)
    return

  def bind(self, obj):
    self.objs.add(obj)
    obj.connect(self)
    return

  def __eq__(self, obj):
    return (isinstance(obj, DictItem) and
            self.objs == obj.objs)
  def __hash__(self):
    return hash(tuple(sorted(self.objs)))


##  SubRef
##
class SubRef(CompoundTypeNode):
  
  def __init__(self, tree, refobj, subs):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.refobj = refobj
    self.objs = set()
    self.subs = subs
    self.refobj.connect(self)
    return

  def __repr__(self):
    return '%r[%s]' % (self.refobj, ':'.join(map(repr, self.subs)))

  def recv(self, src):
    if src == self.refobj:
      self.objs.update(src.types)
      for obj in self.objs:
        obj.get_element(self.subs).connect(self)
    else:
      self.update(src.types)
    return


##  SubAssign
##
class SubAssign(CompoundTypeNode):
  
  def __init__(self, tree, refobj, subs, value):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.objs = set()
    self.subs = subs
    self.value = value
    self.refobj = refobj
    self.refobj.connect(self)
    return

  def __repr__(self):
    return 'assign(%r%r, %r)' % (self.refobj, self.subs, self.value)

  def recv(self, src):
    assert src is self.refobj
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
  
  def __init__(self, tree, refobj):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.refobj = refobj
    self.refobj.connect(self)
    return

  def __repr__(self):
    return 'iter(%r)' % (self.refobj,)

  def recv(self, src):
    if src is self.refobj:
      for obj in src.types:
        try:
          obj.get_iter().connect(self)
        except NodeTypeError:
          Reporter.warn(self.tree, '%r might not be an iterator' % (obj))
          continue
    else:
      self.update(src.types)
    return

    
##  ModuleType
##
class ModuleType(FuncType):
  
  def __init__(self, tree, parent, name):
    FuncType.__init__(self, tree, parent, name, (), (), False, False)
    self.space.register_var('__name__').bind(PrimitiveType(None, ''))
    self.set_code(tree.node)
    self.attrs = {}
    FunCall(tree, self, ())
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
  return ModuleType(tree, GLOBAL_NAMESPACE, name)


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
