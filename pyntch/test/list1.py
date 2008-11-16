#!/usr/bin/env python

def foo(x):
  x[2] = 'a'
  return

a = [1,2,3]
b = a
a[1]=6.6
c = a
foo(b)
x = c[2]
a += ['a']
