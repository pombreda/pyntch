#!/usr/bin/env python
class A:
  def __init__(self, x):
    print 'init!'
    self.x = x
    return 'A'
  def foo(self):
    print 'foo!'
    return 1

class B(A):
  def __init__(self):
    print 'fioo'
  def foo(self):
    print 'foo2!'
  def bar(self):
    print 'bar!'

a=A()
b=B()
x=a.foo()
