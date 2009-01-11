#!/usr/bin/env python

from compiler import ast
from typenode import CompoundTypeNode


##  Variable
##
class Variable(CompoundTypeNode):

  def __init__(self, space, name):
    self.space = space
    self.name = name
    CompoundTypeNode.__init__(self)
    return
  
  def __repr__(self):
    return '@'+self.fullname()

  def fullname(self):
    return '%s.%s' % (self.space.name, self.name)

  def bind(self, obj):
    obj.connect(self)
    return

  
##  Namespace
##
class Namespace:

  debug = 0
  modpath = []

  def __init__(self, parent_space, name):
    self.parent_space = parent_space
    self.name = name
    self.vars = {}
    self.msgs = []
    if parent_space:
      self.name = parent_space.name+'.'+name
      self.global_space = parent_space.global_space
    else:
      self.global_space = self
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
    from module import load_module
    
    if isinstance(tree, ast.Module):
      self.register_names(tree.node)
      
    # global
    elif isinstance(tree, ast.Global):
      for name in tree.names:
        self.vars[name] = self.global_space.register_var(name)

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
        module = load_module(modname, modpath=self.modpath, debug=self.debug)
        self.register_var(asname)
        self[asname].bind(module)

    # from
    elif isinstance(tree, ast.From):
      module = load_module(tree.modname, modpath=self.modpath, debug=self.debug)
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
          isinstance(tree, ast.Power)):
      self.register_names(tree.left)
      self.register_names(tree.right)
    elif isinstance(tree, ast.Compare):
      self.register_names(tree.expr)
      for (_,node) in tree.ops:
        self.register_names(node)
    elif (isinstance(tree, ast.UnaryAdd) or isinstance(tree, ast.UnarySub)):
      self.register_names(tree.expr)
    elif (isinstance(tree, ast.And) or isinstance(tree, ast.Or) or
          isinstance(tree, ast.Bitand) or
          isinstance(tree, ast.Bitor) or isinstance(tree, ast.Bitxor)):
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
    
    # generator expression
    elif isinstance(tree, ast.GenExpr):
      gen = tree.code
      self.register_names(gen.expr)
      for qual in gen.quals:
        self.register_names(qual.iter)
        self.register_names(qual.assign)
        for qif in qual.ifs:
          self.register_names(qif.test)
    
    else:
      raise SyntaxError('unsupported syntax: %r (%s:%r)' % (tree, tree._modname, tree.lineno))
    return

  def import_all(self, space):
    for (k,v) in space.vars.iteritems():
      self.vars[k] = v
    return


