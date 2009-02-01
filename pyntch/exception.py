#!/usr/bin/env python
import sys
stderr = sys.stderr

from compiler import ast
from typenode import TypeNode, SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, \
     BuiltinType, BuiltinObject


##  ExceptionType
##
##  ExceptionType is a built-in Python type so it should be
##  defined within the basic_types module, but it's used
##  throughout the entire program so we define it here for a
##  convenience.
##
class ExceptionObject(BuiltinObject):

  def __init__(self, typeobj, message, args=None):
    self.typeobj = typeobj
    self.message = message
    self.args = args
    SimpleTypeNode.__init__(self, typeobj)
    return

  def __repr__(self):
    return '<%s: %s>' % (self.get_type().get_name(), self.message)

  def get_attr(self, name, write=False):
    from basic_types import StrType
    if name == 'args':
      return self.args # XXX None is returned.
    if name == 'message':
      return StrType.get_object()
    raise NodeAttrError(name)

class ExceptionType(BuiltinType):

  TYPE_NAME = 'Exception'
  TYPE_INSTANCE = ExceptionObject
  OBJECTS = {}

  @classmethod
  def occur(klass, message):
    k = (klass.get_typeobj(), message)
    if k in klass.OBJECTS:
      expt = klass.OBJECTS[k]
    else:
      expt = klass.TYPE_INSTANCE(klass.get_typeobj(), message)
      klass.OBJECTS[k] = expt
    return expt
  maybe = occur

class TracebackObject(TypeNode):

  def __init__(self, expt, loc=None):
    self.expt = expt
    self.loc = loc
    TypeNode.__init__(self, [self])
    return

  def __repr__(self):
    if self.loc:
      return '%s at %s(%s)' % (self.expt, self.loc._module.get_loc(), self.loc.lineno)
    else:
      return '%s at ???' % (self.expt)

  def desc1(self, _):
    return repr(self)

class StopIterationType(ExceptionType):
  TYPE_NAME = 'StopIteration'
class StandardErrorType(ExceptionType):
  TYPE_NAME = 'StandardError'
class ArithmeticErrorType(StandardErrorType):
  TYPE_NAME = 'ArithmeticError'
class FloatingPointErrorType(ArithmeticErrorType):
  TYPE_NAME = 'FloatingPointError'
class OverflowErrorType(ArithmeticErrorType):
  TYPE_NAME = 'OverflowError'
class ZeroDivisionErrorType(ArithmeticErrorType):
  TYPE_NAME = 'ZeroDivisionError'
class AssertionErrorType(StandardErrorType):
  TYPE_NAME = 'AssertionError'
class AttributeErrorType(StandardErrorType):
  TYPE_NAME = 'AttributeError'
class EnvironmentErrorType(StandardErrorType):
  TYPE_NAME = 'EnvironmentError'
class IOErrorType(EnvironmentErrorType):
  TYPE_NAME = 'IOError'
class OSErrorType(EnvironmentErrorType):
  TYPE_NAME = 'OSError'
class WindowsErrorType(OSErrorType):
  TYPE_NAME = 'OSError' # I mean WindowsError.
class VMSErrorType(OSErrorType):
  TYPE_NAME = 'OSError' # I mean VMSError.
class EOFErrorType(StandardErrorType):
  TYPE_NAME = 'EOFError'
class ImportErrorType(StandardErrorType):
  TYPE_NAME = 'ImportError'
class LookupErrorType(StandardErrorType):
  TYPE_NAME = 'LookupError'
class IndexErrorType(LookupErrorType):
  TYPE_NAME = 'IndexError'
class KeyErrorType(LookupErrorType):
  TYPE_NAME = 'KeyError'
class MemoryErrorType(StandardErrorType):
  TYPE_NAME = 'MemoryError'
class NameErrorType(StandardErrorType):
  TYPE_NAME = 'NameError'
class UnboundLocalErrorType(NameErrorType):
  TYPE_NAME = 'UnboundLocalError'
class ReferenceErrorType(StandardErrorType):
  TYPE_NAME = 'ReferenceError'
class RuntimeErrorType(StandardErrorType):
  TYPE_NAME = 'RuntimeError'
class NotImplementedErrorType(RuntimeErrorType):
  TYPE_NAME = 'NotImplementedError'
class SyntaxErrorType(StandardErrorType):
  TYPE_NAME = 'SyntaxError'
class IndentationErrorType(SyntaxErrorType):
  TYPE_NAME = 'IndentationError'
class TabErrorType(IndentationErrorType):
  TYPE_NAME = 'TabError'
class SystemErrorType(StandardErrorType):
  TYPE_NAME = 'SystemError'
class TypeErrorType(StandardErrorType):
  TYPE_NAME = 'TypeError'
class ValueErrorType(StandardErrorType):
  TYPE_NAME = 'ValueError'
class UnicodeErrorType(ValueErrorType):
  TYPE_NAME = 'UnicodeError'
class UnicodeDecodeErrorType(UnicodeErrorType):
  TYPE_NAME = 'UnicodeDecodeError'
class UnicodeEncodeErrorType(UnicodeErrorType):
  TYPE_NAME = 'UnicodeEncodeError'
class UnicodeTranslateErrorType(UnicodeErrorType):
  TYPE_NAME = 'UnicodeTranslateError'


##  ExecutionFrame
##
##  An ExecutionFrame object is a place where an exception belongs.
##  Normally it's a body of function. Exceptions that are raised
##  within this frame are propagated to other ExecutionFrames which
##  invoke the function.
##
class ExecutionFrame(object):

  debug = 0

  class ExceptionAnnotator(CompoundTypeNode):
    
    def __init__(self, frame):
      self.frame = frame
      CompoundTypeNode.__init__(self)
      return

    def __repr__(self):
      return '<Exceptions at %r>' % self.frame
    
    def recv(self, src):
      for obj in src:
        assert isinstance(obj, TracebackObject), obj
        if not obj.loc: obj.loc = self.frame.loc
        self.update_type(obj)
      return

  def __init__(self, parent=None, loc=None):
    self.loc = loc
    self.annotator = self.ExceptionAnnotator(self)
    if parent:
      self.connect_expt(parent)
    return

  def connect_expt(self, frame):
    assert isinstance(frame, ExecutionFrame)
    if self.debug:
      print >>stderr, 'connect_expt: %r <- %r' % (frame, self)
    self.annotator.connect(frame.annotator)
    return
  
  def raise_expt(self, expt):
    if self.debug:
      print >>stderr, 'raise_expt: %r <- %r' % (self, expt)
    TracebackObject(expt).connect(self.annotator)
    return

  def associate_frame(self, frame):
    return

  def show(self, p):
    for expt in self.annotator:
      p('  raises %r' % expt)
    return


##  ExceptionCatcher
##
class ExceptionCatcher(ExecutionFrame):

  class ExceptionFilter(CompoundTypeNode):
    
    def __init__(self, catcher):
      self.catcher = catcher
      self.handlers = {}
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      if self.catcher.catchall: return
      for obj in src:
        assert isinstance(obj, TracebackObject), obj
        for expt in obj.expt:
          try:
            var = self.handlers[expt.get_type()]
            expt.connect(var)
          except KeyError:
            self.update_type(obj)
      return

    def recv_expt(self, src, var):
      for obj in src:
        self.handlers[obj.get_type()] = var
      return

    def catch(self, obj, var):
      obj.connect(self, lambda src: self.recv_expt(src, var))
      return

  def __init__(self, parent):
    self.annotator = self.ExceptionFilter(self)
    self.vars = {}
    self.catchall = False
    self.connect_expt(parent)
    return
  
  def __repr__(self):
    if self.catchall:
      return '<catch all>'
    else:
      return '<catch %s>' % ', '.join(map(repr, self.vars.iterkeys()))

  def add_all(self):
    self.catchall = True
    return
  
  def add_handler(self, src):
    if src not in self.vars:
      self.vars[src] = CompoundTypeNode()
    src.connect(self, self.recv_handler_expt)
    return self.vars[src]

  def recv_handler_expt(self, src):
    from aggregate_types import TupleType
    for obj in src:
      if obj.is_type(TupleType.get_typeobj()):
        self.annotator.catch(obj.elemall, self.vars[src])
      else:
        self.annotator.catch(obj, self.vars[src])
    return


##  MustBeDefinedNode
##
class MustBeDefinedNode(CompoundTypeNode, ExecutionFrame):

  nodes = None
  
  def __init__(self, parent=None, loc=None):
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent=parent, loc=loc)
    MustBeDefinedNode.nodes.append(self)
    return

  def check_undefined(self):
    return
  
  @classmethod
  def reset(klass):
    klass.nodes = []
    return
  
  @classmethod
  def check(klass):
    for node in klass.nodes:
      node.check_undefined()
    return


##  ExceptionMaker
##
##  Special behaviour on raising an exception.
##
class ExceptionMaker(CompoundTypeNode, ExecutionFrame):
  
  def __init__(self, parent, exctype, excargs):
    self.exctype = exctype
    self.excargs = excargs
    CompoundTypeNode.__init__(self)
    ExecutionFrame.__init__(self, parent=parent)
    exctype.connect(self, self.recv_type)
    return
  
  def __repr__(self):
    return '<exception %s>' % (self.describe())

  def recv_type(self, src):
    from function import ClassType
    for obj in src:
      # Instantiate an object only if it is a class object.
      # Otherwise, just return the object given.
      if isinstance(obj, ClassType):
        try:
          result = obj.call(self, self.excargs, {})
        except NodeTypeError:
          self.raise_expt(TypeErrorType.occur('cannot call: %r might be %r' % (self.exctype, obj)))
          continue
        result.connect(self)
      else:
        obj.connect(self)
    return


##  TypeChecker
##
class TypeChecker(CompoundTypeNode):

  ANY = 'any'
  
  def __init__(self, parent_frame, types, blame=None):
    self.parent_frame = parent_frame
    self.blame = blame
    if types == self.ANY:
      self.validtypes = self.ANY
    else:
      self.validtypes = CompoundTypeNode(types)
    CompoundTypeNode.__init__(self)
    return

  def __repr__(self):
    return ('<TypeChecker: %s: %s>' % 
            (','.join(map(repr, self.types)), self.validtypes))

  def recv(self, src):
    if self.validtypes == self.ANY: return
    for obj in src:
      for typeobj in self.validtypes:
        if obj.is_type(typeobj): break
      else:
        s = '|'.join( typeobj.get_name() for typeobj in self.validtypes )
        self.parent_frame.raise_expt(TypeErrorType.occur('%s (%s) must be %s' % (self.blame, obj, s)))
    return


##  SequenceTypeChecker
##
class SequenceTypeChecker(TypeChecker):
  
  def recv(self, src):
    for obj in src:
      try:
        obj.get_seq(self.parent_frame).connect(self, self.recv_elemobj)
      except (NodeTypeError, NodeAttrError):
        if self.blame:
          self.parent_frame.raise_expt(TypeErrorType.occur('%s (%s) must be iterable' % (self.blame, obj)))
    return
  
  def recv_elemobj(self, src):
    if self.validtypes == self.ANY: return
    for obj in src:
      for typeobj in self.validtypes:
        if obj.is_type(typeobj): break
      else:
        s = '|'.join(map(repr, self.validtypes))
        self.parent_frame.raise_expt(TypeErrorType.occur('%s (%s) must be [%s]' % (self.blame, obj, s)))
    return


##  KeyValueTypeChecker
##
class KeyValueTypeChecker(TypeChecker):
  
  def __init__(self, parent_frame, keys, values, blame=None):
    self.validkeys = CompoundTypeNode()
    for obj in keys:
      obj.connect(self.validkeys)
    TypeChecker.__init__(self, parent_frame, values, blame=blame)
    return
    
  def recv(self, src):
    from aggregate_types import DictObject
    for obj in src:
      if isinstance(obj, DictObject):
        obj.key.connect(self, self.recv_key)
        obj.value.connect(self, self.recv_value)
      else:
        if self.blame:
          self.parent_frame.raise_expt(TypeErrorType.occur('%s (%s) must be dictionary' % (self.blame, obj)))
    return
  
  def recv_key(self, src):
    for obj in src:
      if typeobj in self.validkeys:
        if obj.is_type(typeobj):
          self.update_type(obj)
          break
      elif self.blame:
        self.parent_frame.raise_expt(TypeErrorType.occur(
          'key %s (%s) must be [%s]' % (self.blame, obj, '|'.join(map(repr, self.validkeys)))))
    return

  def recv_value(self, src):
    for obj in src:
      if typeobj in self.validtypes:
        if obj.is_type(typeobj):
          self.update_type(obj)
          break
      elif self.blame:
        self.parent_frame.raise_expt(TypeErrorType.occur(
          'value %s (%s) must be [%s]' % (self.blame, obj, '|'.join(map(repr, self.validtypes)))))
    return

