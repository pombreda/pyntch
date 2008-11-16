#!/usr/bin/env python

def foo(x):
  return x

if __name__ == '__main__':
  b = ('a',None,99)
  (x,y) = foo(b)
  (x,y,z) = foo(b)
  (x,(y,z)) = (1,(2,'a'))
  m = b[1]
  return
