#!/usr/bin/env python
import sys
stderr = sys.stderr

from typenode import TypeNode, SimpleTypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, \
     BuiltinType, BuiltinObject
from klass import ClassType, InstanceObject


##  ExceptionType
##
##  ExceptionType is a built-in Python type so it should be
##  defined within the basic_types module, but it's used
##  throughout the entire program so we define it here for a
##  convenience.
##
class ExceptionObject(InstanceObject):

  def __init__(self, klass, message=None):
    self.message = message
    InstanceObject.__init__(self, klass)
    return

  def __repr__(self):
    return '<%s: %s>' % (self.klass.get_name(), self.message)


##  ExceptionType
##
class ExceptionType(ClassType):

  TYPE_NAME = 'Exception'
  OBJECTS = {}

  def __init__(self):
    ClassType.__init__(self, self.TYPE_NAME, [])
    return

  @classmethod
  def occur(klass, message):
    k = (klass.get_typeobj(), message)
    if k in klass.OBJECTS:
      expt = klass.OBJECTS[k]
    else:
      expt = ExceptionObject(klass.get_typeobj(), message)
      klass.OBJECTS[k] = expt
    return expt
  maybe = occur

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


##  TypeChecker
##
class TypeChecker(CompoundTypeNode):

  ANY = 'any'
  
  def __init__(self, parent_frame, types, blame=None):
    self.parent_frame = parent_frame
    self.blame = blame
    self.done = set()
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
      if obj in self.done: continue
      self.done.add(obj)
      for typeobj in self.validtypes:
        if obj.is_type(typeobj): break
      else:
        s = '|'.join( typeobj.get_name() for typeobj in self.validtypes )
        self.parent_frame.raise_expt(TypeErrorType.occur('%s (%s) must be %s' % (self.blame, obj, s)))
    return


##  SequenceTypeChecker
##
class SequenceTypeChecker(TypeChecker):
  
  def __init__(self, parent_frame, types, blame=None):
    self.elemdone = set()
    TypeChecker.__init__(self, parent_frame, types, blame=blame)
    return
  
  def recv(self, src):
    from aggregate_types import ElementGetter
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      try:
        ElementGetter(obj, self.parent_frame).connect(self, self.recv_elemobj)
      except (NodeTypeError, NodeAttrError):
        if self.blame:
          self.parent_frame.raise_expt(TypeErrorType.occur('%s (%s) must be iterable' % (self.blame, obj)))
    return
  
  def recv_elemobj(self, src):
    if self.validtypes == self.ANY: return
    for obj in src:
      if obj in self.elemdone: continue
      self.elemdone.add(obj)
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
    self.keydone = set()
    self.valuedone = set()
    for obj in keys:
      obj.connect(self.validkeys)
    TypeChecker.__init__(self, parent_frame, values, blame=blame)
    return
    
  def recv(self, src):
    from aggregate_types import DictObject
    for obj in src:
      if obj in self.done: continue
      self.done.add(obj)
      if isinstance(obj, DictObject):
        obj.key.connect(self, self.recv_key)
        obj.value.connect(self, self.recv_value)
      else:
        if self.blame:
          self.parent_frame.raise_expt(TypeErrorType.occur('%s (%s) must be dictionary' % (self.blame, obj)))
    return
  
  def recv_key(self, src):
    for obj in src:
      if obj in self.keydone: continue
      self.keydone.add(obj)
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
      if obj in self.valuedone: continue
      self.valuedone.add(obj)
      if typeobj in self.validtypes:
        if obj.is_type(typeobj):
          self.update_type(obj)
          break
      elif self.blame:
        self.parent_frame.raise_expt(TypeErrorType.occur(
          'value %s (%s) must be [%s]' % (self.blame, obj, '|'.join(map(repr, self.validtypes)))))
    return

