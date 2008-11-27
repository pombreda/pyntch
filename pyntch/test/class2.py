#!/usr/bin/env python

class A:
  
  def __init__(self, x):
    print 'init A'
    self.x = x
    return 'A'
  
  def foo(self):
    print 'foo!'
    return 1

class B(A):
  
  def __init__(self):
    print 'initb'
    
  def foo(self):
    print 'foo2!'
    
  def bar(self):
    print 'bar!'

a = A(123)
b = B()
x = a.foo()

