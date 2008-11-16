#!/usr/bin/env python

def foo(x):
  if x == 0:
    return 0
  return bar(x-1)

def bar(y):
  if y == 0:
    return 1
  return foo(y-1)

if __name__ == '__main__':
  print foo(1)
  print bar(1)
