#!/usr/bin/env python

def foo(x):
  return x

if __name__ == '__main__':
  a = 99
  b = ('a',None,a)
  (x,y) = foo(b)
  (x,y,z) = foo(b)
  (x,(y,z)) = (1,(2,'a'))
  m = b[1]
  b[1] = 0
  print b+b
  return
