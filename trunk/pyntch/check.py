#!/usr/bin/env python

import sys, os.path
from typenode import TypeNode
from exception import ExecutionFrame, MustBeDefinedNode
from namespace import Namespace
from module import Interpreter

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
  modpath = ['stub']+sys.path[:]
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-p': modpath.extend(v.split(':'))
  TypeNode.debug = debug
  #ExecutionFrame.debug = debug
  #Namespace.debug = debug
  #Interpreter.debug = debug
  Interpreter.initialize(modpath)
  for fname in args:
    print '===', fname, '==='
    MustBeDefinedNode.reset()
    if fname.endswith('.py'):
      module = Interpreter.load_file(fname, '__main__')
    else:
      module = Interpreter.load_module(fname)
    MustBeDefinedNode.check()
    module.showrec(sys.stdout)
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
