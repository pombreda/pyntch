#!/usr/bin/env python

from compiler import ast
from typenode import TypeNode, UndefinedTypeNode
from exception import ExceptionFrame, ExceptionCatcher, ExceptionMaker, TypeChecker
from exception import NameErrorType, RuntimeErrorType
from function import FuncType, LambdaFuncType, ClassType
from expression import AttrAssign, AttrRef, SubAssign, SubRef, IterRef, SliceAssign, SliceRef, \
     FunCall, BinaryOp, CompareOp, BooleanOp, AssignOp, UnaryOp, NotOp, IfExpOp, TupleUnpack


##  build_assign(reporter, frame, namespace, node1, node2, evals)
##
def build_assign(reporter, frame, space, n, v, evals):
  if isinstance(n, ast.AssName) or isinstance(n, ast.Name):
    space[n.name].bind(v)
  elif isinstance(n, ast.AssTuple):
    tup = TupleUnpack(frame, n, v, len(n.nodes))
    for (i,c) in enumerate(n.nodes):
      build_assign(reporter, frame, space, c, tup.get_nth(i), evals)
  elif isinstance(n, (ast.AssAttr, ast.Getattr)):
    obj = build_expr(reporter, frame, space, n.expr, evals)
    AttrAssign(frame, n, obj, n.attrname, v)
  elif isinstance(n, ast.Subscript):
    obj = build_expr(reporter, frame, space, n.expr, evals)
    subs = [ build_expr(reporter, frame, space, expr, evals) for expr in n.subs ]
    SubAssign(frame, n, obj, subs, v)
  elif isinstance(n, ast.Slice):
    obj = build_expr(reporter, frame, space, n.expr, evals)
    lower = upper = None
    if n.lower:
      lower = build_expr(reporter, frame, space, n.lower, evals)
    if n.upper:
      upper = build_expr(reporter, frame, space, n.upper, evals)
    SliceAssign(frame, n, obj, lower, upper, v)
  else:
    raise SyntaxError('unsupported syntax: %r (%s:%r)' % (n, n._module.get_name(), n.lineno))
  return


##  build_expr(reporter, frame, namespace, tree, evals)
##
##  Constructs a TypeNode from a given syntax tree.
##
def build_expr(reporter, frame, space, tree, evals):
  from basic_types import BUILTIN_OBJECTS, GeneratorSlot
  from aggregate_types import IterType, ListType, DictType, TupleType

  if isinstance(tree, ast.Const):
    typename = type(tree.value).__name__
    expr = BUILTIN_OBJECTS[typename]

  elif isinstance(tree, ast.Name):
    try:
      expr = space[tree.name]
    except KeyError:
      ExceptionFrame(frame, tree).raise_expt(NameErrorType.occur('name %r is not defined.' % tree.name))
      expr = UndefinedTypeNode(tree.name)

  elif isinstance(tree, ast.CallFunc):
    func = build_expr(reporter, frame, space, tree.node, evals)
    args = tuple( build_expr(reporter, frame, space, arg1, evals)
                  for arg1 in tree.args if not isinstance(arg1, ast.Keyword) )
    kwargs = dict( (arg1.name, build_expr(reporter, frame, space, arg1.expr, evals))
                   for arg1 in tree.args if isinstance(arg1, ast.Keyword) )
    # XXX handle: tree.star_args, tree.dstar_args
    expr = FunCall(frame, tree, func, args, kwargs)

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
    expr = TupleType.create_sequence(elements=elements)

  elif isinstance(tree, ast.List):
    elements = [ build_expr(reporter, frame, space, node, evals) for node in tree.nodes ]
    expr = ListType.create_sequence(elements=elements)

  elif isinstance(tree, ast.Dict):
    items = [ (build_expr(reporter, frame, space, k, evals),
               build_expr(reporter, frame, space, v, evals))
              for (k,v) in tree.items ]
    expr = DictType.create_dict(items=items)

  # +, -, *, /, %, //, **, <<, >>
  elif isinstance(tree, (ast.Add, ast.Sub, ast.Mul, ast.Div,
                         ast.Mod, ast.FloorDiv, ast.Power,
                         ast.LeftShift, ast.RightShift)):
    op = tree.__class__.__name__
    left = build_expr(reporter, frame, space, tree.left, evals)
    right = build_expr(reporter, frame, space, tree.right, evals)
    expr = BinaryOp(frame, tree, op, left, right)
    
  # &, |, ^
  elif isinstance(tree, (ast.Bitand, ast.Bitor, ast.Bitxor)):
    op = tree.__class__.__name__
    nodes = [ build_expr(reporter, frame, space, node, evals) for node in tree.nodes ]
    expr = nodes.pop(0)
    for right in nodes:
      expr = BinaryOp(frame, tree, op, expr, right)
  
  # ==, !=, <=, >=, <, >, in, not in, is, is not
  elif isinstance(tree, ast.Compare):
    expr0 = build_expr(reporter, frame, space, tree.expr, evals)
    comps = [ (op, build_expr(reporter, frame, space, node, evals)) for (op,node) in tree.ops ]
    expr = CompareOp(frame, tree, expr0, comps)

  # +,-
  elif isinstance(tree, (ast.UnaryAdd, ast.UnarySub)):
    op = tree.__class__.__name__
    value = build_expr(reporter, frame, space, tree.expr, evals)
    expr = UnaryOp(frame, tree, op, value)

  # and, or
  elif isinstance(tree, (ast.And, ast.Or)):
    op = tree.__class__.__name__
    nodes = [ build_expr(reporter, frame, space, node, evals) for node in tree.nodes ]
    expr = BooleanOp(frame, tree, op, nodes)

  # not
  elif isinstance(tree, ast.Not):
    value = build_expr(reporter, frame, space, tree.expr, evals)
    expr = NotOp(frame, tree, value)

  # lambda
  elif isinstance(tree, ast.Lambda):
    defaults = [ build_expr(reporter, frame, space, value, evals) for value in tree.defaults ]
    expr = LambdaFuncType(reporter, frame, space, tree.argnames,
                          defaults, tree.varargs, tree.kwargs, tree.code, tree)

  # list comprehension
  elif isinstance(tree, ast.ListComp):
    elements = [ build_expr(reporter, frame, space, tree.expr, evals) ]
    expr = ListType.create_sequence(elements)
    for qual in tree.quals:
      seq = build_expr(reporter, frame, space, qual.list, evals)
      build_assign(reporter, frame, space, qual.assign, IterRef(frame, qual.list, seq), evals)
      for qif in qual.ifs:
        build_expr(reporter, frame, space, qif.test, evals)

  # generator expression
  elif isinstance(tree, ast.GenExpr):
    gen = tree.code
    elements = [ build_expr(reporter, frame, space, gen.expr, evals) ]
    expr = IterType.create_sequence(elements)
    for qual in gen.quals:
      seq = build_expr(reporter, frame, space, qual.iter, evals)
      build_assign(reporter, frame, space, qual.assign, IterRef(frame, qual.iter, seq), evals)
      for qif in qual.ifs:
        build_expr(reporter, frame, space, qif.test, evals)

  # yield (for python 2.5)
  elif isinstance(tree, ast.Yield):
    value = build_expr(reporter, frame, space, tree.value, evals)
    expr = GeneratorSlot(value)
    evals.append(('y', expr)) # XXX ???

  # ifexp
  elif isinstance(tree, ast.IfExp):
    test = build_expr(reporter, frame, space, tree.test, evals)
    then = build_expr(reporter, frame, space, tree.then, evals)
    else_ = build_expr(reporter, frame, space, tree.else_, evals)
    expr = IfExpOp(frame, tree, test, then, else_)

  elif isinstance(tree, ast.Backquote):
    ExceptionFrame(frame, tree).raise_expt(RuntimeErrorType.occur('backquote is not supported.'))
    expr = UndefinedTypeNode('backquote')

  else:
    # unsupported AST.
    raise SyntaxError('unsupported syntax: %r (%s:%r)' % (tree, tree._module.get_loc(), tree.lineno))

  assert isinstance(expr, (TypeNode, tuple)), expr
  evals.append((None, expr))
  return expr


##  build_typecheck(reporter, frame, space, tree, msg, evals)
##
def build_typecheck(reporter, frame, space, tree, msg, evals):
  # "assert isinstance() and isinstance() and ...
  if isinstance(tree, ast.CallFunc):
    tests = [ tree ]
  elif isinstance(tree, ast.And):
    tests = tree.nodes
  else:
    return
  for node in tests:
    if (isinstance(node, ast.CallFunc) and
        isinstance(node.node, ast.Name) and
        node.node.name == 'isinstance' and
        len(node.args) == 2):
      (a,b) = node.args
      if msg and isinstance(msg, ast.Const):
        blame = msg.value
      elif isinstance(a, ast.Name):
        blame = repr(a.name)
      else:
        blame = repr(a)
      tc = TypeChecker(frame, [build_expr(reporter, frame, space, b, evals)], blame)
      build_expr(reporter, frame, space, a, evals).connect(tc)
  return


##  build_stmt
##
def build_stmt(reporter, frame, space, tree, evals, isfuncdef=False):
  from basic_types import NoneType, StrType
  assert isinstance(frame, ExceptionFrame)

  if isinstance(tree, ast.Module):
    build_stmt(reporter, frame, space, tree.node, evals)
  
  # def
  elif isinstance(tree, ast.Function):
    name = tree.name
    defaults = [ build_expr(reporter, frame, space, value, evals) for value in tree.defaults ]
    func = FuncType(reporter, frame, space, name, tree.argnames,
                    defaults, tree.varargs, tree.kwargs, tree.code, tree)
    if tree.decorators:
      for node in tree.decorators:
        decor = build_expr(reporter, frame, space, node, evals)
        func = FunCall(frame, tree, decor, (func,))
    space[name].bind(func)

  # class
  elif isinstance(tree, ast.Class):
    name = tree.name
    bases = [ build_expr(reporter, frame, space, base, evals) for base in tree.bases ]
    klass = ClassType(reporter, frame, space, name, bases, tree.code, evals, tree)
    space[name].bind(klass)

  # assign
  elif isinstance(tree, ast.Assign):
    for n in tree.nodes:
      value = build_expr(reporter, frame, space, tree.expr, evals)
      build_assign(reporter, frame, space, n, value, evals)

  # augassign
  elif isinstance(tree, ast.AugAssign):
    left = build_expr(reporter, frame, space, tree.node, evals)
    if isinstance(left, UndefinedTypeNode):
      ExceptionFrame(frame, tree).raise_expt(NameErrorType.occur('cannot assign to an undefined variable.'))
    else:
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
        value = NoneType.get_object()
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
      expttype = build_expr(reporter, frame, space, tree.expr1, evals)
      exptarg = build_expr(reporter, frame, space, tree.expr2, evals)
      ExceptionFrame(frame, tree).raise_expt(ExceptionMaker(frame, tree, expttype, (exptarg,)))
    elif tree.expr1:
      expttype = build_expr(reporter, frame, space, tree.expr1, evals)
      ExceptionFrame(frame, tree).raise_expt(ExceptionMaker(frame, tree, expttype, ()))

  # printnl
  elif isinstance(tree, (ast.Print, ast.Printnl)):
    for node in tree.nodes:
      value = build_expr(reporter, frame, space, node, evals)
      value.connect(StrType.StrConvChecker(frame))

  # discard
  elif isinstance(tree, ast.Discard):
    value = build_expr(reporter, frame, space, tree.expr, evals)

  # pass, break, continue
  elif isinstance(tree, (ast.Pass, ast.Break, ast.Continue)):
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
    build_typecheck(reporter, frame, space, tree.test, tree.fail, evals)
    build_expr(reporter, frame, space, tree.test, evals)
    if tree.fail:
      build_expr(reporter, frame, space, tree.fail, evals)

  # unsupported
  elif isinstance(tree, ast.Exec):
    ExceptionFrame(frame, tree).raise_expt(RuntimeErrorType.occur('exec is not supported.'))
  
  else:
    raise SyntaxError('unsupported syntax: %r (%s:%r)' % (tree, tree._module.get_loc(), tree.lineno))

  return