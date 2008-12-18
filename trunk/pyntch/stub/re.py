#!/usr/bin/env python

I = IGNORECASE = 0
L = LOCALE = 0
U = UNICODE = 0
M = MULTILINE = 0
S = DOTALL = 0
X = VERBOSE = 0
T = TEMPLATE = 0
DEBUG = 0

class rematch:
  def group(self, i=0):
    return
  def groups(self):
    return

class compile:
  def __init__(self, pattern, flags=0):
    return
  def search(self, string, flags=0):
    if 1:
      return None
    else:
      return rematch()
  def match(self, string, flags=0):
    if 1:
      return None
    else:
      return rematch()
  def sub(self, repl, string, count=0):
    return string
  def subn(self, repl, string, count=0):
    return (string, 0)
  def split(self, string, maxsplit=0):
    return ['']
  def findall(self, string, flags=0):
    return 
  def findall(self, string, flags=0):
    return [rematch()]
  def finditer(self, string, flags=0):
    return ['']

def match(pattern, string, flags=0):
  return compile(pattern, flags).match(string)
def search(pattern, string, flags=0):
  return compile(pattern, flags).search(string)
def sub(pattern, repl, string, count=0):
  return compile(pattern).sub(repl, string, count)
def subn(pattern, repl, string, count=0):
  return compile(pattern).subn(repl, string, count)
def split(pattern, string, maxsplit=0):
  return compile(pattern).split(string, maxsplit)
def findall(pattern, string, flags=0):
  return compile(pattern, flags).findall(string)
def finditer(pattern, string, flags=0):
  return compile(pattern, flags).finditer(string)
def escape(pattern):
  return pattern
