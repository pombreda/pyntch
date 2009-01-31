#!/usr/bin/env python

a1 = list()
a2 = list([1,2,3])
a3 = list('abc')

b1 = [1,2,3]
b1[1] = 'x'
b2 = b1.pop(10)

c = [4,5,6]
c.append('b')
c.remove(123)
c.count('a')
c.index(123)
c.extend('b')
c.extend(1)
c.extend(c)

e = [1,2,3]
e.reverse()
e.sort()
e.sort(key=lambda x:x+1)
e.sort(reverse=True)
e.sort(cmp=lambda x,y:1)

f1 = b1[:1]
f2 = b1[1:3]
f3 = b1[3:]
f4 = b1['f']

h = [1,2,3]
h[:2] = 'a'
h[1:2] = [1,2]

