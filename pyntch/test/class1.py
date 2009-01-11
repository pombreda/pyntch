#!/usr/bin/env python

class A:
  
  a = 1
  
  def __init__(self, x):
    self.x = x
    self.a = 'a'
    A.b = 2
    return
  
  def foo(self, x):
    self.y = x
    return 'B'

a = A(123)
a.foo(456)
