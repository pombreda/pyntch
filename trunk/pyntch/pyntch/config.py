#!/usr/bin/env python

from exception import SyntaxErrorType, TypeErrorType, ValueErrorType, \
     AttributeErrorType, IndexErrorType, IOErrorType, EOFErrorType, \
     KeyErrorType, NameErrorType, RuntimeErrorType, OSErrorType, \
     UnicodeDecodeErrorType, UnicodeEncodeErrorType

class ErrorConfig(object):

  # occur
  @classmethod
  def RaiseOutsideTry(klass):
    return SyntaxErrorType.occur('raise with no argument outside try-except')
  
  @classmethod
  def NameUndefined(klass, name):
    return NameErrorType.occur('undefined: %s' % name)

  @classmethod
  def NotSupported(klass, name):
    return RuntimeErrorType.occur('unsupported feature: %s' % name)
  
  @classmethod
  def NotCallable(klass, obj):
    return TypeErrorType.occur('not callable: %r' % obj)
  
  @classmethod
  def NotInstantiatable(klass, typename):
    return TypeErrorType.occur('not instantiatable: %s' % typename)
  
  @classmethod
  def NoKeywordArgs(klass):
    return TypeErrorType.occur('cannot take a keyword argument')
  
  @classmethod
  def NoKeywordArg1(klass, kwd):
    return TypeErrorType.occur('cannot take keyword: %s' % kwd)
  
  @classmethod
  def InvalidKeywordArgs(klass, kwd):
    return TypeErrorType.occur('invalid keyword argument: %s' % kwd)
  
  @classmethod
  def InvalidNumOfArgs(klass, valid, nargs):
    if valid < nargs:
      return TypeErrorType.occur('too many args: %r required, %r given' % (valid, nargs))
    else:
      return TypeErrorType.occur('too few args: %r given, %r required' % (nargs, valid))

  @classmethod
  def NotConvertable(klass, typename):
    return ValueErrorType.occur('not convertable to %s' % typename)

  @classmethod
  def NotIterable(klass, obj):
    return TypeErrorType.occur('not iterable: %r' % obj)
  
  @classmethod
  def NotSubscriptable(klass, obj):
    return TypeErrorType.occur('not subscriptable: %r' % obj)
  
  @classmethod
  def NotAssignable(klass, obj):
    return TypeErrorType.occur('cannot assign item: %r' % obj)
  
  @classmethod
  def NoLength(klass, obj):
    return TypeErrorType.occur('length not defined' % obj)
  
  @classmethod
  def AttributeNotFound(klass, obj, attrname):
    return AttributeErrorType.occur('attribute not found: %r.%s' % (obj, attrname))
  
  @classmethod
  def AttributeNotAssignable(klass, obj, attrname):
    return AttributeErrorType.occur('attribute cannot be assigned: %r.%s' % (obj, attrname))
  
  @classmethod
  def NotUnpackable(klass, obj):
    return ValueErrorType.occur('tuple cannot be unpacked: %r' % obj)
  
  @classmethod
  def NotSupportedOperand(klass, op, left, right=None):
    if right:
      return TypeErrorType.occur('unsupported operand %s(%s, %s)' % (op, left.describe(), right.describe()))
    else:
      return TypeErrorType.occur('unsupported operand %s(%s)' % (op, left.describe()))

  @classmethod
  def TypeCheckerError(klass, src, obj, validtype):
    return TypeErrorType.occur('%s (%s) must be %s' % (src, obj ,validtype))

  # maybe
  @classmethod
  def MaybeNotConvertable(klass, typename):
    return ValueErrorType.maybe('not convertable to %s' % typename)
  @classmethod
  def MaybeOutOfRange(klass):
    return IndexErrorType.maybe('index out of range')
  @classmethod
  def MaybeKeyNotFound(klass):
    return KeyErrorType.maybe('key not found')
  @classmethod
  def MaybeElementNotFound(klass):
    return ValueErrorType.maybe('element not found')
  @classmethod
  def MaybeElementNotRemovable(klass):
    return ValueErrorType.maybe('empty container')
  @classmethod
  def MaybeNotRemovable(klass):
    return ValueErrorType.maybe('cannot remove an entry')
  @classmethod
  def MaybeNotDecodable(klass):
    return UnicodeDecodeErrorType.maybe('unicode not decodable')
  @classmethod
  def MaybeNotEncodable(klass):
    return UnicodeEncodeErrorType.maybe('unicode not encodable')
  @classmethod
  def MaybeSubstringNotFound(klass):
    return ValueErrorType.maybe('substring not found')
  @classmethod
  def MaybeTableInvalid(klass):
    return ValueErrorType.maybe('translate table invalid')
  @classmethod
  def MaybeFileCannotOpen(klass):
    return IOErrorType.maybe('cannot open a file')
  @classmethod
  def MaybeFileIllegalSeek(klass):
    return IOErrorType.maybe('illegal seek')
  @classmethod
  def MaybeEOFError(klass):
    return EOFErrorType.maybe('end of file')
  
  def __init__(self):
    return

  def load(self, fname):
    return
