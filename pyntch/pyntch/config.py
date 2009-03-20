#!/usr/bin/env python

from exception import SyntaxErrorType, TypeErrorType, ValueErrorType, \
     IndexErrorType, IOErrorType, EOFErrorType, \
     NameErrorType, RuntimeErrorType, OSErrorType, \
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
  def NotCallable(klass, src, obj):
    return TypeErrorType.occur('not callable: %r might be %r' % (src, obj))
  
  @classmethod
  def NotInstantiatable(klass, typename):
    return TypeErrorType.occur('not instantiatable: %s' % typename)
  
  @classmethod
  def NoKeywordArgs(klass):
    return TypeErrorType.occur('cannot take a keyword argument')
  
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
  def TypeCheckerError(klass, src, obj, validtype):
    return TypeErrorType.occur('%s (%s) must be %s' % (src, obj ,validtype))

  @classmethod
  def AttributeNotFound(klass, obj, attrname):
    return AttributeErrorType.occur('attribute not found: %r.%s' % (obj ,attrname))
  
  # maybe
  @classmethod
  def MaybeNotConvertable(klass, typename):
    return ValueErrorType.maybe('not convertable to %s' % typename)
  @classmethod
  def MaybeOutOfRange(klass):
    return IndexErrorType.maybe('index out of range')
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
