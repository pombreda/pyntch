#!/usr/bin/env python

import sys, os.path
from pyntch.typenode import TypeNode, CompoundTypeNode
from pyntch.frame import ExecutionFrame
from pyntch.expression import MustBeDefinedNode
from pyntch.namespace import Namespace
from pyntch.module import Interpreter

# main
def main(argv):
  import getopt
  def usage():
    print 'usage: %s [-d] [-p pythonpath] [file ...]' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'dp:')
  except getopt.GetoptError:
    return usage()
  debug = 0
  verbose = 1
  modpath = ['stub']+sys.path[:]
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-p': modpath.extend(v.split(':'))
  TypeNode.debug = debug
  TypeNode.verbose = verbose
  #ExecutionFrame.debug = debug
  #Namespace.debug = debug
  #Interpreter.debug = debug
  Interpreter.initialize(modpath)
  for name in args:
    print '===', name, '==='
    MustBeDefinedNode.reset()
    if name.endswith('.py'):
      path = name
      (name,_) = os.path.splitext(os.path.basename(name))
      module = Interpreter.load_file(path, name)
    else:
      module = Interpreter.load_module(name)
    MustBeDefinedNode.check()
    module.showall(sys.stdout)
  TypeNode.showstat()
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
