#!/usr/bin/env python
# module: 'os'

import posixpath as path
import errno
from posix import *

SEEK_CUR = 0
SEEK_END = 0
SEEK_SET = 0

name = 'posix'
curdir = ''
pardir = ''
sep = ''
extsep = ''
altsep = ''
pathsep = ''
linesep = ''
defpath = ''
devnull = ''

class error(EnvironmentError):
  pass

OSError = error
WindowsError = error
VMSError = error

execl = function() # XXX
execle = function() # XXX
execlp = function() # XXX
execlpe = function() # XXX

execvp = _execvp
execvpe = _execvpe

def getenv(k):
  assert isinstance(k, str)
  return environ[k]

popen2 = function() # XXX
popen3 = function() # XXX
popen4 = function() # XXX

makedirs = function() # XXX
removedirs = function() # XXX
renames = function() # XXX

P_NOWAIT = 0
P_NOWAITO = 0
P_WAIT = 0

spawnl = function() # XXX
spawnle = function() # XXX
spawnlp = function() # XXX
spawnlpe = function() # XXX
spawnv = function() # XXX
spawnve = function() # XXX
spawnvp = function() # XXX
spawnvpe = function() # XXX

def urandom(n):
  assert isinstance(n, int)
  return ''

def walk(top, topdown=True, onerror=None):
  return
