#!/usr/bin/env python

import sys, os, os.path
import pyntch
from pyntch.typenode import TypeNode, CompoundTypeNode
from pyntch.frame import ExecutionFrame
from pyntch.expression import MustBeDefinedNode
from pyntch.namespace import Namespace
from pyntch.module import Interpreter, IndentedStream
from pyntch.config import ErrorConfig

# main
def main(argv):
  import getopt
  def usage():
    print 'usage: %s [-d] [-c config] [-p pythonpath] [file ...]' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'dc:p:')
  except getopt.GetoptError:
    return usage()
  stubdir = os.path.join(os.path.dirname(pyntch.__file__), 'stub')
  debug = 0
  verbose = 1
  modpath = [stubdir]+sys.path[:]
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-c': ErrorConfig.load(v)
    elif k == '-p': modpath.extend(v.split(':'))
  TypeNode.debug = debug
  TypeNode.verbose = verbose
  #ExecutionFrame.debug = debug
  #Namespace.debug = debug
  #Interpreter.debug = debug
  Interpreter.initialize(modpath)
  MustBeDefinedNode.reset()
  modules = []
  for name in args:
    if name.endswith('.py'):
      path = name
      (name,_) = os.path.splitext(os.path.basename(name))
      module = Interpreter.load_file(path, name)
    else:
      module = Interpreter.load_module(name)
    modules.append(module)
  MustBeDefinedNode.check()
  TypeNode.showstat()
  for module in modules:
    print '===', module.get_name(), '==='
    module.showrec(IndentedStream(sys.stdout))
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
