#!/usr/bin/env python

def range(x):
  return [1]

def foo(x):
  x[2] = x
  return

a = [1,2,3]
b = a
foo(b)
x = b[2]
y = [ j+1 for j in range(10) ]

for i in a:
  print i
