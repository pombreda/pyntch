#!/usr/bin/env python

class A: pass
class B(A): pass
class C(A): pass

try:
  raise B
except A:
  print 'A'

try:
  raise A
except B:
  print 'B'

try:
  raise B
  raise C
except (B,C):
  print 'B,C'

try:
  raise 'foo'
except str:
  print 'str'
