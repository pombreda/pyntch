#!/usr/bin/env python

from pyntch.typenode import TypeNode, CompoundTypeNode, NodeTypeError, NodeAttrError, \
     BuiltinType, BuiltinObject
from pyntch.klass import ClassType, InstanceObject


##  ExceptionType
##
##  ExceptionType is a built-in Python type so it should be
##  defined within the basic_types module, but it's used
##  throughout the entire program so we define it here for a
##  convenience.
##
class InternalException(InstanceObject):

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

  def get_attr(self, frame, anchor, name, write=False):
    if name == '__init__':
      return self.InitMethod(self)
    return ClassType.get_attr(self, frame, anchor, name, write=write)

  @classmethod
  def occur(klass, message):
    k = (klass.get_typeobj(), message)
    if k in klass.OBJECTS:
      expt = klass.OBJECTS[k]
    else:
      expt = InternalException(klass.get_typeobj(), message)
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
  
  def __init__(self, parent_frame, types, blame):
    self.parent_frame = parent_frame
    self.blame = blame
    self.received = set()
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
    from pyntch.config import ErrorConfig
    from pyntch.basic_types import TypeType
    if self.validtypes == self.ANY: return
    for obj in src:
      if obj in self.received: continue
      self.received.add(obj)
      for typeobj in self.validtypes:
        if typeobj.is_type(TypeType.get_typeobj()) and obj.is_type(typeobj): break
      else:
        s = '|'.join( typeobj.get_name() for typeobj in self.validtypes
                      if typeobj.is_type(TypeType.get_typeobj()) )
        self.parent_frame.raise_expt(ErrorConfig.TypeCheckerError(self.blame, obj, s))
    return


##  SequenceTypeChecker
##
class SequenceTypeChecker(TypeChecker):
  
  def __init__(self, parent_frame, anchor, types, blame):
    self.anchor = anchor
    self.received = set()
    self.received_elem = set()
    TypeChecker.__init__(self, parent_frame, types, blame=blame)
    return
  
  def recv(self, src):
    from pyntch.expression import IterElement
    for obj in src:
      if obj in self.received: continue
      self.received.add(obj)
      IterElement(self.parent_frame, self.anchor, obj).connect(self.recv_elemobj)
    return
  
  def recv_elemobj(self, src):
    from pyntch.config import ErrorConfig
    if self.validtypes == self.ANY: return
    for obj in src:
      if obj in self.received_elem: continue
      self.received_elem.add(obj)
      for typeobj in self.validtypes:
        if obj.is_type(typeobj): break
      else:
        s = '[%s]' % ('|'.join(map(repr, self.validtypes)))
        self.parent_frame.raise_expt(ErrorConfig.TypeCheckerError(self.blame, obj, s))
    return


##  KeyValueTypeChecker
##
class KeyValueTypeChecker(TypeChecker):
  
  def __init__(self, parent_frame, keys, values, blame):
    self.validkeys = CompoundTypeNode(keys)
    self.received_key = set()
    self.received_value = set()
    TypeChecker.__init__(self, parent_frame, values, blame=blame)
    return
    
  def recv(self, src):
    from pyntch.config import ErrorConfig
    from pyntch.aggregate_types import DictObject
    for obj in src:
      if obj in self.received: continue
      self.received.add(obj)
      if isinstance(obj, DictObject):
        obj.key.connect(self.recv_key)
        obj.value.connect(self.recv_value)
      else:
        self.parent_frame.raise_expt(ErrorConfig.TypeCheckerError(self.blame, obj, 'dict'))
    return
  
  def recv_key(self, src):
    from pyntch.config import ErrorConfig
    for obj in src:
      if obj in self.received_key: continue
      self.received_key.add(obj)
      for typeobj in self.validkeys:
        if obj.is_type(typeobj):
          self.update_type(obj)
          break
      else:
        s = '|'.join(map(repr, self.validkeys))
        self.parent_frame.raise_expt(ErrorConfig.TypeCheckerError('key of %s' % self.blame, obj, s))
    return

  def recv_value(self, src):
    from pyntch.config import ErrorConfig
    for obj in src:
      if obj in self.received_value: continue
      self.received_value.add(obj)
      for typeobj in self.validtypes:
        if obj.is_type(typeobj):
          self.update_type(obj)
          break
      else:
        s = '|'.join(map(repr, self.validtypes))
        self.parent_frame.raise_expt(ErrorConfig.TypeCheckerError('value of %s' % self.blame, obj, s))
    return
