#!/usr/bin/env python

class A:
  
  def __init__(self, x):
    self.x = x
    return
  
  def __repr__(self):
    return '<A:%r>' % self.x
  
  def __eq__(self, a):
    print '__eq__', self, a
    return self.x == a.x

a = A(1)
b = A(1)
print a
print a == b
