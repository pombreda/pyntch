#!/usr/bin/env python

def foo(x):
  x[2] = 3
  return

a = ['a','b','c']
a += [5]
c = range(10)
c.append(3.14)
a[0] = c[4]
b = a
foo(b)
