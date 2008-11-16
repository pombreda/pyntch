#!/usr/bin/env python

def foo(d):
  d[1]='b'
  return

a = {1:'a', 'b':'c', [1,2]:'x'}
b = a
a[1]=6.6
c = a
foo(b)
x = c[2]
