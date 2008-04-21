#!/usr/bin/env python
import sys, os.path, compiler
from compiler.ast import *

stdout = sys.stdout
stderr = sys.stderr
debug = 1

PATHS = ['.']


##  Report
##
class Report:

  msgs = {}
  subspaces = {}

  @classmethod
  def put(klass, tree, s):
    if tree not in klass.msgs:
      klass.msgs[tree] = []
    klass.msgs[tree].append(s)
    return

  warn = put
  info = put

  @classmethod
  def register(klass, tree, node):
    klass.subspaces[tree] = node
    return
  
  @classmethod
  def show(klass, tree, fp=sys.stdout, level=0):
    if tree in klass.subspaces:
      klass.subspaces[tree].finish()
      level += 1
    if tree in klass.msgs:
      lineno = tree.lineno
      indent = ' '*level
      for msg in klass.msgs[tree]:
        fp.write(indent+'%s: %s\n' % (lineno, msg))
    for node in tree.getChildNodes():
      klass.show(node, fp, level)
    return
  

##  TypeNode
##
class TypeNode:

  def __init__(self, *types):
    self.types = set(types)
    self.sendto = set()
    return

  def connect(self, node):
    assert isinstance(node, CompoundTypeNode), node
    if node in self.sendto: return
    if debug:
      print >>stderr, 'connect: %r -> %r' % (self,node)
    self.sendto.add(node)
    node.recv(self)
    return

  def recv(self, src):
    raise TypeError('SimpleTypeNode cannot receive a value.')

  def get_proc(self):
    raise TypeError('not callable')
  def get_element(self, _, write=False):
    raise TypeError('not subscriptable')
  def get_attr(self, _, write=False):
    raise TypeError('no attribute')
  
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
    return

  def update(self, types):
    diff = types.difference(self.types)
    if diff:
      self.types.update(diff)
      for node in list(self.sendto):
        node.recv(self)
    return


##  PrimitiveType
##
class PrimitiveType(SimpleTypeNode):
  
  def __init__(self, tree, typeobj):
    self.typename = type(typeobj).__name__
    SimpleTypeNode.__init__(self)
    self.tree = tree
    return

  def __repr__(self):
    return '<%s>' % self.typename

  def __eq__(self, obj):
    return isinstance(obj, PrimitiveType) and self.typename == obj.typename
  def __hash__(self):
    return hash(self.typename)


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

  def recv(self, src):
    self.update(src.types)
    return

  def bind(self, obj):
    obj.connect(self)
    return

  
##  Namespace
##
class Namespace:

  def __init__(self, parent, name, code=None):
    self.parent = parent
    self.name = name
    self.vars = {}
    self.subspaces = {}
    self.msgs = []
    if parent:
      self.name = parent.name+'.'+name
    if code:
      self.register_names(code)
    return
  
  def __repr__(self):
    return '<Namespace: %s>' % self.name

  def __contains__(self, name):
    return name in self.vars
  
  def __getitem__(self, name):
    return self.get_var(name)

  def to_attrs(self):
    return self.vars.iteritems()

  def get_var(self, name):
    while self:
      if name in self.vars:
        return self.vars[name]
      self = self.parent
    raise KeyError(name)

  def get_subspace(self, tree):
    return self.subspaces[tree]

  def register_var(self, name):
    if name not in self.vars:
      self.vars[name] = Variable(self, name)
    return
  
  def register_subspace(self, tree, subspace):
    if tree not in self.subspaces:
      self.subspaces[tree] = subspace
    return
  
  # register_names
  def register_names(self, tree):
    # def
    if isinstance(tree, Function):
      space1 = Namespace(self, tree.name, tree.code)
      for name in tree.argnames:
        space1.register_var(name)
      self.register_var(tree.name)
      self.register_subspace(tree, space1)

    # class
    elif isinstance(tree, Class):
      space1 = Namespace(self, tree.name, tree.code)
      self.register_var(tree.name)
      self.register_subspace(tree, space1)

    # assign
    elif isinstance(tree, Assign):
      for c in tree.nodes:
        self.register_names(c)
      self.register_names(tree.expr)
    elif isinstance(tree, AssTuple):
      for c in tree.nodes:
        self.register_names(c)
    elif isinstance(tree, AssName):
      self.register_var(tree.name)
    elif isinstance(tree, AssAttr):
      self.register_names(tree.expr)
    elif isinstance(tree, Subscript):
      self.register_names(tree.expr)

    # (mutliple statements)
    elif isinstance(tree, Stmt):
      for stmt in tree.nodes:
        self.register_names(stmt)

    # if, elif, else
    elif isinstance(tree, If):
      for (expr,stmt) in tree.tests:
        self.register_names(expr)
        self.register_names(stmt)
      if tree.else_:
        self.register_names(tree.else_)

    # for
    elif isinstance(tree, For):
      self.register_names(tree.list)
      self.register_names(tree.assign)
      self.register_names(tree.body)
      if tree.else_:
        self.register_names(tree.else_)

    # while
    elif isinstance(tree, While):
      self.register_names(tree.test)
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
      self.register_names(tree.expr)
    elif isinstance(tree, Return):
      self.register_names(tree.value)
    elif isinstance(tree, Break):
      pass
    elif isinstance(tree, Continue):
      pass
    elif isinstance(tree, Raise):
      self.register_names(tree.expr1)
      self.register_names(tree.expr2)
    elif isinstance(tree, Assert):
      self.register_names(tree.test)
    elif isinstance(tree, Printnl):
      for node in tree.nodes:
        self.register_names(node)
    elif isinstance(tree, Print):
      pass
    elif isinstance(tree, Yield):
      self.register_names(tree.value)
    elif isinstance(tree, Exec):
      pass
    elif isinstance(tree, Pass):
      pass
    
    # expressions
    elif isinstance(tree, Const):
      pass
    elif isinstance(tree, Name):
      pass
    elif isinstance(tree, CallFunc):
      pass
    elif isinstance(tree, Getattr):
      pass
    elif isinstance(tree, Tuple):
      pass
    elif isinstance(tree, List):
      for node in tree.nodes:
        self.register_names(node)
    # +, -, *, /, %, //, <<, >>, **, &, |, ^
    elif (isinstance(tree, Add) or isinstance(tree, Sub) or
          isinstance(tree, Mul) or isinstance(tree, Div) or
          isinstance(tree, Mod) or isinstance(tree, FloorDiv) or
          isinstance(tree, LeftShift) or isinstance(tree, RightShift) or
          isinstance(tree, Power) or isinstance(tree, Bitand) or
          isinstance(tree, Bitor) or isinstance(tree, Bitxor)):
      self.register_names(tree.left)
      self.register_names(tree.right)
    # ==, !=, <=, >=, <, >
    elif isinstance(tree, Compare):
      self.register_names(tree.expr)
      for (_,node) in tree.ops:
        self.register_names(node)
    # +,-
    elif isinstance(tree, UnaryAdd) or isinstance(tree, UnarySub):
      self.register_names(tree.expr)
    # and, or
    elif (isinstance(tree, And) or isinstance(tree, Or)):
      for node in tree.nodes:
        self.register_names(node)
    # not
    elif isinstance(tree, Not):
      self.register_names(tree.expr)
    # lambda
    elif isinstance(tree, Lambda):
      tmpname = '__lambda%x' % id(tree)
      space1 = Namespace(self, tmpname, tree.code)
      for name in tree.argnames:
        space1.register_var(name)
      self.register_subspace(tree, space1)

    else:
      raise SyntaxError(tree)
    return

  def import_all(self, space):
    for (k,v) in space.vars.iteritems():
      self.vars[k] = v
    for (k,v) in space.subspaces.iteritems():
      self.subspaces[k] = v
    return


##  GlobalNamespace
##
class GlobalNamespace(Namespace):
  def __init__(self):
    Namespace.__init__(self, None, '')
    self.register_var('True')
    self.register_var('False')
    self.register_var('None')
    self['None'].bind(PrimitiveType(None, None))
    return

GLOBAL_NAMESPACE = GlobalNamespace()


##  ModuleType
##
class ModuleType(SimpleTypeNode):
  
  def __init__(self, name, space, code):
    SimpleTypeNode.__init__(self)
    self.space = space
    self.name = name
    self.code = code
    return
  
  def __repr__(self):
    return '<Module %s>' % self.name


##  BuiltinNamespace
##
class BuiltinNamespace(Namespace):
  
  def __init__(self, name):
    Namespace.__init__(self, GLOBAL_NAMESPACE, name)
    return

class BuiltinModuleType(ModuleType):
  def __init__(self, name):
    ModuleType.__init__(self, name, BuiltinNamespace(name), None)
    return

BUILTIN_MODULE = {
  'sys': BuiltinModuleType('sys'),
}

# find_module
def find_module(name):
  fname = name+'.py'
  for dirname in PATHS:
    path = os.path.join(dirname, name)
    if os.path.exists(path):
      return path
    path = os.path.join(dirname, fname)
    if os.path.exists(path):
      return path
  raise ImportError(name)

# load_module
def load_module(modname, asname=None):
  if modname in BUILTIN_MODULE:
    return BUILTIN_MODULE[modname]
  path = find_module(modname)
  name = asname or modname
  module = compiler.parseFile(path)
  space1 = Namespace(GLOBAL_NAMESPACE, name, module.node)
  space1.register_var('__name__')
  module = ModuleType(name, space1, module.node)
  return module




# build_expr
def build_expr(space, tree):

  if isinstance(tree, Const):
    expr = PrimitiveType(tree, tree.value)

  elif isinstance(tree, Name):
    expr = space[tree.name]

  elif isinstance(tree, CallFunc):
    func = build_expr(space, tree.node)
    args = tuple( build_expr(space, arg1) for arg1 in tree.args )
    expr = FunCall(tree, func, args)

  elif isinstance(tree, Getattr):
    obj = build_expr(space, tree.expr)
    expr = AttrRef(tree, obj, tree.attrname)

  elif isinstance(tree, Subscript):
    obj = build_expr(space, tree.expr)
    subs = [ build_expr(space, sub) for sub in tree.subs ]
    expr = SubRef(tree, obj, subs)

  elif isinstance(tree, Tuple):
    elements = [ build_expr(space, node) for node in tree.nodes ]
    expr = TupleType(tree, elements)

  elif isinstance(tree, List):
    elements = [ build_expr(space, node) for node in tree.nodes ]
    expr = ListType(tree, elements)

  # +, -, *, /, %, //, <<, >>, **, &, |, ^
  elif (isinstance(tree, Add) or isinstance(tree, Sub) or
        isinstance(tree, Mul) or isinstance(tree, Div) or
        isinstance(tree, Mod) or isinstance(tree, FloorDiv) or
        isinstance(tree, LeftShift) or isinstance(tree, RightShift) or
        isinstance(tree, Power) or isinstance(tree, Bitand) or
        isinstance(tree, Bitor) or isinstance(tree, Bitxor)):
    op = tree.__class__.__name__
    left = build_expr(space, tree.left)
    right = build_expr(space, tree.right)
    expr = BinaryOp(tree, op, left, right)

  # ==, !=, <=, >=, <, >
  elif isinstance(tree, Compare):
    expr0 = build_expr(space, tree.expr)
    comps = [ (op, build_expr(space, node)) for (op,node) in tree.ops ]
    expr = CompareOp(tree, expr0, comps)

  # +,-
  elif isinstance(tree, UnaryAdd) or isinstance(tree, UnarySub):
    value = build_expr(space, tree.expr)
    expr = UnaryOp(tree.__class__, value)

  # and, or
  elif (isinstance(tree, And) or isinstance(tree, Or)):
    nodes = [ build_expr(space, node) for node in tree.nodes ]
    expr = BooleanOp(tree, tree.__class__.__name__, nodes)

  # not
  elif isinstance(tree, Not):
    value = build_expr(space, tree.expr)
    expr = NotOp(tree, value)

  # lambda
  elif isinstance(tree, Lambda):
    tmpname = '__lambda%x' % id(tree)
    subspace = space.get_subspace(tree)
    expr = FuncType(tree, tmpname, subspace, tree.argnames, tree.code, lambdaexp=True)

  else:
    raise SyntaxError(tree)

  assert isinstance(expr, TypeNode)
  return expr


# build_stmt
def build_stmt(space, tree, evals, isfuncdef=False):

  def assign(n, v):
    if isinstance(n, AssName):
      space[n.name].bind(v)
    elif isinstance(n, AssTuple):
      vars = [ space[c.name] for c in n.nodes ]
      TupleUnpack(n, v, vars)
    elif isinstance(n, AssAttr):
      obj = build_expr(space, n.expr)
      evals.append((0, obj))
      AttrAssign(n, obj, n.attrname, v)
    elif isinstance(n, Subscript):
      obj = build_expr(space, n.expr)
      evals.append((0, obj))
      subs = [ build_expr(space, expr) for expr in n.subs ]
      evals.extend( (False, sub) for sub in subs )
      SubAssign(n, obj, subs, v)
    else:
      raise TypeError(n)
    return

  # def
  if isinstance(tree, Function):
    name = tree.name
    subspace = space.get_subspace(tree)
    space[name].bind(FuncType(tree, name, subspace, tree.argnames, tree.code))

  # class
  elif isinstance(tree, Class):
    name = tree.name
    subspace = space.get_subspace(tree)
    bases = [ build_expr(space, base) for base in tree.bases ]
    space[name].bind(ClassType(tree, name, subspace, bases, tree.code, evals))

  # assign
  elif isinstance(tree, Assign):
    for n in tree.nodes:
      value = build_expr(space, tree.expr)
      evals.append((0, value))
      assign(n, value)

  # return
  elif isinstance(tree, Return):
    value = build_expr(space, tree.value)
    evals.append((1, value))

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
      value = build_expr(space, expr)
      evals.append((0, value))
      build_stmt(space, stmt, evals)
    if tree.else_:
      build_stmt(space, tree.else_, evals)

  # for
  elif isinstance(tree, For):
    seq = build_expr(space, tree.list)
    evals.append((0, seq))
    assign(tree.assign, IterRef(seq))
    build_stmt(space, tree.body, evals)
    if tree.else_:
      build_stmt(space, tree.else_, evals)

  # while
  elif isinstance(tree, While):
    value = build_expr(space, tree.test)
    evals.append((0, value))
    build_stmt(space, tree.body, evals)
    if tree.else_:
      build_stmt(space, tree.else_, evals)

  # try ... except
  elif isinstance(tree, TryExcept):
    build_stmt(space, tree.body, evals)
    #XXX exceptions.update(__)
    for (exc,e,stmt) in tree.handlers:
      value = build_expr(space, exc)
      evals.append((0, value))
      assign(e, value)
      build_stmt(space, stmt, evals)
    if tree.else_:
      build_stmt(space, tree.else_, evals)

  # try ... finally
  elif isinstance(tree, TryFinally):
    build_stmt(space, tree.body, evals)
    build_stmt(space, tree.final, evals)

  # yield
  elif isinstance(tree, Yield):
    value = build_expr(space, tree.value)
    evals.append((2, value)) # XXX

  # printnl
  elif isinstance(tree, Printnl):
    for node in tree.nodes:
      value = build_expr(space, node)
      evals.append((0, value))

  # discard
  elif isinstance(tree, Discard):
    value = build_expr(space, tree.expr)
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
    evals.append((0, build_expr(space, tree.expr)))
  elif isinstance(tree, Subscript):
    evals.append((0, build_expr(space, tree.expr)))

  else:
    raise SyntaxError(tree)

  return


##  FuncBodyType
##
class FuncBodyType(CompoundTypeNode):

  def __init__(self, name, evals):
    CompoundTypeNode.__init__(self)
    self.name = name
    self.retvals = []
    for (is_retval,obj) in evals:
      if is_retval:
        self.retvals.append(obj)
      obj.connect(self)
    return

  def __repr__(self):
    return '<FuncBody %s>' % self.name
  
  def recv(self, src):
    if src in self.retvals:
      self.update(src.types)
    return


##  FuncType
##
class FuncType(SimpleTypeNode):
  
  def __init__(self, tree, name, space, argnames, code, lambdaexp=False):
    SimpleTypeNode.__init__(self)
    Report.register(tree, self)
    self.tree = tree
    self.space = space
    self.name = name
    self.argnames = argnames
    self.args = tuple( space[argname] for argname in argnames )
    evals = []
    if lambdaexp:
      evals.append((1, build_expr(space, code)))
    else:
      build_stmt(space, code, evals, isfuncdef=True)
    self.body = FuncBodyType(self.name, evals)
    return

  def __repr__(self):
    return ('<Function %s>' % (self.name,))

  def bind_args(self, args):
    for (var,arg1) in zip(self.args, args):
      arg1.connect(var)
    return
  
  def get_proc(self):
    return self.body

  def finish(self):
    Report.info(self.tree, 'def: args=[%s], body=%s' %
                (','.join(self.argnames), self.body))
    return


##  BoundFuncType
##
class BoundFuncType(SimpleTypeNode):
  
  def __init__(self, arg0, func):
    SimpleTypeNode.__init__(self)
    self.arg0 = arg0
    self.func = func
    if len(func.args) < 1:
      raise TypeError('no argument')
    return
  
  def __repr__(self):
    return '<BoundFuncType %r(%s=%r)>' % (self.func, self.func.argnames[0], self.arg0)
  
  def bind_args(self, args):
    self.func.bind_args((self.arg0,)+args)
    return
  
  def get_proc(self):
    return self.func.get_proc()


##  FunCall
##
class FunCall(CompoundTypeNode):
  
  def __init__(self, tree, func, args):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.func = func
    self.args = args
    self.funcs = set()
    self.func.connect(self)
    return

  def __repr__(self):
    return '<%r(%s)>' % (self.func, ','.join(map(repr, self.args)))

  def recv(self, src):
    if src is self.func:
      self.funcs.update(src.types)
      for func in self.funcs:
        try:
          proc = func.get_proc()
        except TypeError:
          Report.warn(self.tree, 'cannot call: %r might be %r' % (self.func, func))
          continue
        func.bind_args(self.args)
        proc.connect(self)
    else:
      self.update(src.types)
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
  
  def recv(self, src):
    assert src == self.left or src == self.right
    self.update(src.types)
    return


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
    return 'cmp(%r %s)' % (self.expr0, ','.join( '%s %r' % (op,expr) for (op,expr) in self.comps ))
  
  def recv(self, _):
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
  
  def recv(self, src):
    self.update(src.types)
    return


##  ListType
##
class ListType(SimpleTypeNode):
  
  def __init__(self, tree, elements):
    SimpleTypeNode.__init__(self)
    self.tree = tree
    self.elem = ListElement(self, elements)
    return
  
  def __repr__(self):
    return '[%s]' % self.elem

  def desc1(self, done):
    return '[%s]' % self.elem.desc1(done)

  def get_element(self, _=False):
    return self.elem

class ListElement(CompoundTypeNode):
  
  def __init__(self, parent, elements):
    CompoundTypeNode.__init__(self)
    self.parent = parent
    self.elements = elements
    for elem in self.elements:
      elem.connect(self)
    return

  def __repr__(self):
    return '|'.join(map(str, self.elements))
  
  def recv(self, src):
    self.update(src.types)
    return
  

##  TupleType
##
class TupleType(SimpleTypeNode):
  
  def __init__(self, tree, elements):
    SimpleTypeNode.__init__(self)
    self.tree = tree
    self.elements = elements
    self.elemall = TupleElement(self, elements)
    return
  
  def __repr__(self):
    return '(%s)' % ','.join(map(repr, self.elements))

  def desc1(self, done):
    return '(%s)' % ','.join( elem.desc1(done) for elem in self.elements )

  def get_nth(self, i):
    return self.elements[i]

  def get_element(self, write=False):
    if write:
      raise TypeError('cannot change tuple')
    return self.elemall

class TupleElement(CompoundTypeNode):
  
  def __init__(self, parent, elements):
    CompoundTypeNode.__init__(self)
    self.parent = parent
    self.elements = elements
    for elem in self.elements:
      elem.connect(self)
    return

  def __repr__(self):
    return '|'.join(map(str, self.elements))
  
  def recv(self, src):
    self.update(src.types)
    return
  
class TupleUnpack(CompoundTypeNode):

  def __init__(self, tree, refobj, vars):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.refobj = refobj
    self.vars = vars
    self.refobj.connect(self)
    return

  def recv(self, src):
    assert src is self.refobj
    for obj in src.types:
      if isinstance(obj, TupleType):
        if len(obj.elements) != len(self.vars):
          Report.warn(self.tree, 'tuple elements mismatch: len(%r) != %r' %
                      (obj, len(self.vars)))
        else:
          for (i,elem) in enumerate(obj.elements):
            self.vars[i].bind(elem)
      else:
        pass
    return


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
    if src is self.refobj:
      self.objs.update(src.types)
      for obj in self.objs:
        obj.get_element().connect(self)
    else:
      self.update(src.types)
    return


##  SubAssign
##
class SubAssign(CompoundTypeNode):
  
  def __init__(self, tree, refobj, subs, value):
    CompoundTypeNode.__init__(self)
    self.tree = tree
    self.refobj = refobj
    self.objs = set()
    self.subs = subs
    self.value = value
    self.refobj.connect(self)
    return

  def __repr__(self):
    return 'assign(%r%r, %r)' % (self.refobj, self.subs, self.value)

  def recv(self, src):
    assert src is self.refobj
    self.objs.update(src.types)
    for obj in self.objs:
      self.value.connect(obj.get_element(write=True))
    return


##  ClassType
##
class ClassType(SimpleTypeNode):
  
  def __init__(self, tree, name, space, bases, code, evals):
    SimpleTypeNode.__init__(self)
    Report.register(tree, self)
    self.tree = tree
    self.name = name
    self.space = space
    self.bases = bases
    self.attrs = {}
    for (name, value) in space.to_attrs():
      value.connect(self.add_attr(name))
    self.instance = InstanceType(self, self.attrs.iteritems())
    self.initbody = InitMethodBody(self.instance)
    build_stmt(space, code, evals)
    return

  def __repr__(self):
    return ('<Class %s>' % (self.name,))

  def add_attr(self, name):
    attr = ClassAttr(name, self)
    self.attrs[name] = attr
    return attr

  def get_attr(self, name, write=False):
    if write and (name not in self.attrs):
      return self.add_attr(name)
    return self.attrs[name]

  def bind_args(self, args):
    return self.initbody.bind_args(args)
  
  def get_proc(self):
    return self.initbody

  def finish(self):
    for (_, attr) in sorted(self.attrs.iteritems()):
      Report.info(self.tree, 'class.%s = %s' % (attr.name, attr.describe()))
    for (_, attr) in sorted(self.instance.attrs.iteritems()):
      Report.info(self.tree, 'instance.%s = %s' % (attr.name, attr.describe()))
    return


##  ClassAttr
##
class ClassAttr(CompoundTypeNode):
  
  def __init__(self, name, klass):
    CompoundTypeNode.__init__(self)
    self.name = name
    self.klass = klass
    return

  def __repr__(self):
    return '%r.@%s' % (self.klass, self.name)
  
  def recv(self, src):
    self.update(src.types)
    return


##  InitMethodBody
##
class InitMethodBody(CompoundTypeNode):
  
  def __init__(self, instance):
    CompoundTypeNode.__init__(self, instance)
    self.funcs = set()
    try:
      self.initfunc = instance.get_attr('__init__')
      self.initfunc.connect(self)
    except KeyError:
      self.initfunc = None
    return

  def __repr__(self):
    return '<InitMethodBody %r>' % self.initfunc

  def bind_args(self, args):
    for func in self.funcs:
      func.bind_args(args)
    return

  def recv(self, src):
    if src is self.initfunc:
      self.funcs.update(src.types)
      for func in self.funcs:
        try:
          proc = func.get_proc()
        except TypeError:
          Report.warn(self.tree, 'cannot call: %r might be %r' % (self.func, func))
          continue
        proc.connect(self)
    else:
      # ignore return value
      pass
    return


##  InstanceType
##
class InstanceType(SimpleTypeNode):
  
  def __init__(self, klass, attrs):
    SimpleTypeNode.__init__(self)
    self.klass = klass
    self.attrs = {}
    for (name, value) in attrs:
      value.connect(self.add_attr(name))
    return
  
  def __repr__(self):
    return ('<Instance %s>' % (self.klass.name,))

  def add_attr(self, name):
    attr = InstanceAttr(name, self.klass, self)
    self.attrs[name] = attr
    return attr

  def get_attr(self, name, write=False):
    if write and (name not in self.attrs):
      return self.add_attr(name)
    return self.attrs[name]


##  InstanceAttr
##
class InstanceAttr(CompoundTypeNode):
  
  def __init__(self, name, klass, instance):
    CompoundTypeNode.__init__(self)
    self.name = name
    self.klass = klass
    self.instance = instance
    return

  def __repr__(self):
    return '%r.@%s' % (self.instance, self.name)
  
  def recv(self, src):
    types = set()
    for obj in src.types:
      if isinstance(obj, FuncType):
        try:
          obj = BoundFuncType(self.instance, obj)
          # XXX
          #elif isinstance(obj, ClassMethodType):
          #elif isinstance(obj, StaticMethodType):
        except TypeError:
          Report.warn(obj.tree, 'cannot call: %r no arg0' % (obj))
          continue
      types.add(obj)
    self.update(types)
    return


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
    if src is self.refobj:
      self.objs.update(src.types)
      for obj in self.objs:
        try:
          obj.get_attr(self.attrname).connect(self)
        except KeyError:
          Report.warn(self.tree, 'attribute not found: %r.%s' % (obj, self.attrname))
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
      attr = obj.get_attr(self.attrname, write=True)
      self.value.connect(attr)
    return


##  MainFuncType
##
class MainFuncType(FuncType):
  
  def __init__(self, space, code):
    FuncType.__init__(self, None, None, space, (), code)
    FunCall(None, self, ())
    return
  

def main(argv):
  name = argv[1]
  module = load_module(name, '__main__')
  MainFuncType(module.space, module.code)
  Report.show(module.code)
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
