#!/usr/bin/env python
# exception handling

class E():
  def __init__(self, *args):
    return

def foo():
  raise 'this should be propagated'

def bar():
  try:
    raise E('this should not be propagated')
  except E:
    pass

def baz():
  try:
    raise 'this should be propagated'
  except E, e:
    pass

if __name__ == '__main__':
  foo()
  bar()
  baz()

