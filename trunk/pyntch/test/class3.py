#!/usr/bin/env python

class A:
  def __init__(self, x):
    self.x = x
    return
  def __repr__(self):
    return '<A:%r>' % self.x
  def __eqa__(self, a):
    print '__eq__', self, a
    return self.x == a.x

a=[A(1), A(2)]
b=[A(1), A(2)]
print a == b
