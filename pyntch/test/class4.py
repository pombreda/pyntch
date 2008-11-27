#!/usr/bin/env python

def foo(x):
  class A:
    a = x
    def __init__(self):
      self.x = x
      return
  b = A()
  return b

print foo(123)
