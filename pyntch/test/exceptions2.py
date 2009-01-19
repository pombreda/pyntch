#!/usr/bin/env python

class A: pass
class B(A): pass

try:
  raise B
except A:
  print 'A'

try:
  raise A
except B:
  print 'B'

try:
  raise 'foo'
except str:
  print 'str'
