#!/usr/bin/env python
import sys
stderr = sys.stderr

from compiler import ast
from typenode import TypeNode, BuiltinType, SimpleTypeNode, CompoundTypeNode, NodeTypeError


##  ExceptionType
##
##  ExceptionType is a built-in Python type so it should be
##  defined within the builtin_types module, but it's used
##  throughout the entire program so we define it here for a
##  convenience.
##
class ExceptionType(BuiltinType):

  PYTHON_TYPE = Exception

  @classmethod
  def occur(klass, message):
    return ExceptionObject(klass.get_typeobj(), message)
  maybe = occur

class ExceptionObject(SimpleTypeNode):

  def __init__(self, typeobj, message, args=None):
    self.typeobj = typeobj
    self.message = message
    self.args = args
    SimpleTypeNode.__init__(self, typeobj)
    return

  def __repr__(self):
    return '<%s: %s>' % (self.get_type().get_name(), self.message)

  def get_attr(self, name, write=False):
    from builtin_types import StrType
    if name == 'args':
      return self.args # XXX None is returned.
    if name == 'message':
      return StrType.get_object()
    raise NodeAttrError(name)

class TracebackObject(TypeNode):

  def __init__(self, expt, loc=None):
    self.expt = expt
    self.loc = loc
    TypeNode.__init__(self, [self])
    return

  def __repr__(self):
    if self.loc:
      return '%s at %s(%d)' % (self.expt, self.loc._modname, self.loc.lineno)
    else:
      return '%s at ???' % (self.expt)

  def equal(self, obj, done=None):
    return isinstance(obj, TracebackObject) and self.loc == obj.loc and self.expt.equal(obj.expt, done) 

  def desc1(self, _):
    return repr(self)

class StandardErrorType(ExceptionType):
  PYTHON_TYPE = StandardError
class ArithmeticErrorType(StandardErrorType):
  PYTHON_TYPE = ArithmeticError
class FloatingPointErrorType(ArithmeticErrorType):
  PYTHON_TYPE = FloatingPointError
class OverflowErrorType(ArithmeticErrorType):
  PYTHON_TYPE = OverflowError
class ZeroDivisionErrorType(ArithmeticErrorType):
  PYTHON_TYPE = ZeroDivisionError
class AssertionErrorType(StandardErrorType):
  PYTHON_TYPE = AssertionError
class AttributeErrorType(StandardErrorType):
  PYTHON_TYPE = AttributeError
class EnvironmentErrorType(StandardErrorType):
  PYTHON_TYPE = EnvironmentError
class IOErrorType(EnvironmentErrorType):
  PYTHON_TYPE = IOError
#class OSErrorType(EnvironmentErrorType):
#  PYTHON_TYPE = OSError
#class WindowsErrorType(OSErrorType):
#  PYTHON_TYPE = OSError # I mean WindowsError.
#class VMSErrorType(OSErrorType):
#  PYTHON_TYPE = OSError # I mean VMSError.
class EOFErrorType(StandardErrorType):
  PYTHON_TYPE = EOFError
class ImportErrorType(StandardErrorType):
  PYTHON_TYPE = ImportError
class LookupErrorType(StandardErrorType):
  PYTHON_TYPE = LookupError
class IndexErrorType(LookupErrorType):
  PYTHON_TYPE = IndexError
class KeyErrorType(LookupErrorType):
  PYTHON_TYPE = KeyError
class MemoryErrorType(StandardErrorType):
  PYTHON_TYPE = MemoryError
class NameErrorType(StandardErrorType):
  PYTHON_TYPE = NameError
class UnboundLocalErrorType(NameErrorType):
  PYTHON_TYPE = UnboundLocalError
class ReferenceErrorType(StandardErrorType):
  PYTHON_TYPE = ReferenceError
class RuntimeErrorType(StandardErrorType):
  PYTHON_TYPE = RuntimeError
class NotImplementedErrorType(RuntimeErrorType):
  PYTHON_TYPE = NotImplementedError
class SyntaxErrorType(StandardErrorType):
  PYTHON_TYPE = SyntaxError
class IndentationErrorType(SyntaxErrorType):
  PYTHON_TYPE = IndentationError
class TabErrorType(IndentationErrorType):
  PYTHON_TYPE = TabError
class SystemErrorType(StandardErrorType):
  PYTHON_TYPE = SystemError
class TypeErrorType(StandardErrorType):
  PYTHON_TYPE = TypeError
class ValueErrorType(StandardErrorType):
  PYTHON_TYPE = ValueError
class UnicodeErrorType(ValueErrorType):
  PYTHON_TYPE = UnicodeError
class UnicodeDecodeErrorType(UnicodeErrorType):
  PYTHON_TYPE = UnicodeDecodeError
class UnicodeEncodeErrorType(UnicodeErrorType):
  PYTHON_TYPE = UnicodeEncodeError
class UnicodeTranslateErrorType(UnicodeErrorType):
  PYTHON_TYPE = UnicodeTranslateError


##  ExceptionFrame
##
##  An ExceptionFrame object is a place where an exception belongs.
##  Normally it's a body of function. Exceptions that are raised
##  within this frame are propagated to other ExceptionFrames which
##  invoke the function.
##
class ExceptionFrame(object):

  debug = 0

  class ExceptionAnnotator(CompoundTypeNode):
    
    def __init__(self, loc):
      self.loc = loc
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      for obj in src:
        assert isinstance(obj, TracebackObject), obj
        if not obj.loc: obj.loc = self.loc
        self.update_types([obj])
      return

  def __init__(self, parent=None, loc=None):
    self.loc = loc
    self.annotator = self.ExceptionAnnotator(loc)
    if parent:
      self.connect_expt(parent)
    return

  def connect_expt(self, frame):
    assert isinstance(frame, ExceptionFrame)
    if self.debug:
      print >>stderr, 'connect_expt: %r <- %r' % (frame, self)
    self.annotator.connect(frame.annotator)
    return
  
  def raise_expt(self, expt):
    if self.debug:
      print >>stderr, 'raise_expt: %r <- %r' % (self, expt)
    TracebackObject(expt).connect(self.annotator)
    return

  def show(self, p):
    for expt in self.annotator:
      p('  raises %r' % expt)
    return


##  ExceptionCatcher
##
class ExceptionCatcher(ExceptionFrame):

  class ExceptionFilter(CompoundTypeNode):
    
    def __init__(self, catcher):
      self.catcher = catcher
      CompoundTypeNode.__init__(self)
      return
    
    def recv(self, src):
      if self.catcher.catchall: return
      for obj in src:
        assert isinstance(obj, TracebackObject), obj
        caught = False
        for expt1 in obj.expt:
          for (expt0,var) in self.catcher.handlers.itervalues():
            for typeobj in expt0:
              if expt1.is_type(typeobj):
                expt1.connect(var)
                caught = True
        if not caught:
          self.update_types([obj])
      return

  def __init__(self, parent):
    self.annotator = self.ExceptionFilter(self)
    self.handlers = {}
    self.catchall = False
    self.connect_expt(parent)
    return
  
  def __repr__(self):
    if self.catchall:
      return '<catch all>'
    else:
      return '<catch %s>' % ', '.join(map(repr, self.handlers.iterkeys()))

  def add_all(self):
    self.catchall = True
    return
  
  def add_handler(self, src):
    if src not in self.handlers:
      self.handlers[src] = (CompoundTypeNode(), CompoundTypeNode())
    src.connect(self, self.recv_handler_expt)
    (_,var) = self.handlers[src]
    return var

  def recv_handler_expt(self, src):
    from aggregate_types import TupleType
    (expt,_) = self.handlers[src]
    for obj in src:
      if obj.is_type(TupleType.get_typeobj()):
        obj.elemall.connect(expt)
      else:
        obj.connect(expt)
    return


##  ExceptionRaiser
##
class ExceptionRaiser(ExceptionFrame): pass


##  MustBeDefinedNode
##
class MustBeDefinedNode(CompoundTypeNode, ExceptionRaiser):

  nodes = None
  
  def __init__(self, parent, loc):
    CompoundTypeNode.__init__(self)
    ExceptionRaiser.__init__(self, parent, loc)
    MustBeDefinedNode.nodes.append(self)
    return
  
  @classmethod
  def reset(klass):
    klass.nodes = []
    return
  
  @classmethod
  def check(klass):
    for node in klass.nodes:
      if not node.types:
        node.raise_expt(node.undefined())
    return


##  ExceptionMaker
##
##  Special behaviour on raising an exception.
##
class ExceptionMaker(CompoundTypeNode, ExceptionRaiser):
  
  def __init__(self, parent_frame, loc, exctype, excargs):
    CompoundTypeNode.__init__(self)
    self.exctype = exctype
    self.excargs = excargs
    ExceptionRaiser.__init__(self, parent_frame, loc)
    exctype.connect(self, self.recv_type)
    return
  
  def __repr__(self):
    return '<exception %r(%s)>' % (self.exctype, ','.join(map(repr, self.excargs)))

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
  
  def __init__(self, parent_frame, types, blame=None):
    CompoundTypeNode.__init__(self)
    self.parent_frame = parent_frame
    self.validtypes = CompoundTypeNode()
    self.blame = blame
    if not isinstance(types, (tuple,list)):
      types = (types,)
    for obj in types:
      obj.connect(self.validtypes)
    return

  def __repr__(self):
    return ('<TypeChecker: %s: %s>' % 
            (','.join(map(repr, self.types)), self.validtypes))

  def recv(self, src):
    for obj in src:
      for typeobj in self.validtypes:
        if obj.is_type(typeobj):
          self.update_types([obj])
          break
      else:
        s = '|'.join( typeobj.get_name() for typeobj in self.validtypes )
        self.parent_frame.raise_expt(TypeErrorType.occur('%s (%s) must be %s' % (self.blame, obj, s)))
    return


##  ElementTypeChecker
##
class ElementTypeChecker(TypeChecker):
  
  def recv(self, src):
    for obj in src:
      try:
        obj.get_seq(self.parent_frame).connect(self, self.recv_elemobj)
      except NodeTypeError:
        if self.blame:
          self.parent_frame.raise_expt(TypeErrorType.occur('%s (%s) must be iterable' % (self.blame, obj)))
    return
  
  def recv_elemobj(self, src):
    for obj in src:
      if typeobj in self.validtypes:
        if obj.is_type(typeobj):
          self.update_types([obj])
          break
      elif self.blame:
        self.parent_frame.raise_expt(TypeErrorType.occur(
          '%s (%s) must be [%s]' % (self.blame, obj, '|'.join(map(repr, self.validtypes)))))
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
          self.update_types([obj])
          break
      elif self.blame:
        self.parent_frame.raise_expt(TypeErrorType.occur(
          'key %s (%s) must be [%s]' % (self.blame, obj, '|'.join(map(repr, self.validkeys)))))
    return

  def recv_value(self, src):
    for obj in src:
      if typeobj in self.validtypes:
        if obj.is_type(typeobj):
          self.update_types([obj])
          break
      elif self.blame:
        self.parent_frame.raise_expt(TypeErrorType.occur(
          'value %s (%s) must be [%s]' % (self.blame, obj, '|'.join(map(repr, self.validtypes)))))
    return
