#!/usr/bin/env python

import sys, os, os.path
import pyntch
from pyntch.typenode import TypeNode, CompoundTypeNode
from pyntch.frame import ExecutionFrame
from pyntch.expression import MustBeDefinedNode
from pyntch.namespace import Namespace
from pyntch.module import Interpreter, IndentedStream, ModuleNotFound
from pyntch.config import ErrorConfig

# main
def main(argv):
  import getopt
  def usage():
    print 'usage: %s [-d] [-q] [-a] [-c config] [-C key=val] [-p pythonpath] [file ...]' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'dqac:C:p:')
  except getopt.GetoptError:
    return usage()
  if not args:
    return usage()
  stubdir = os.path.join(os.path.dirname(pyntch.__file__), 'stub')
  debug = 0
  verbose = 1
  modpath = [stubdir]+sys.path[:]
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-q': verbose -= 1
    elif k == '-a': ErrorConfig.show_all = True
    elif k == '-c': ErrorConfig.load(v)
    elif k == '-C':
      (k,v) = v.split('=')
      ErrorConfig.set(k, eval(v))
    elif k == '-p': modpath.extend(v.split(':'))
  TypeNode.debug = debug
  TypeNode.verbose = verbose
  Interpreter.debug = debug
  Interpreter.verbose = verbose
  Interpreter.initialize(modpath)
  MustBeDefinedNode.reset()
  modules = []
  for name in args:
    try:
      if name.endswith('.py'):
        path = name
        (name,_) = os.path.splitext(os.path.basename(name))
        module = Interpreter.load_file(path, name)
      else:
        module = Interpreter.load_module(name)
      modules.append(module)
    except ModuleNotFound, e:
      print >>sys.stderr, 'module not found:', name
  MustBeDefinedNode.check()
  if ErrorConfig.unfound_modules:
    print >>sys.stderr, 'modules not found:', ', '.join(sorted(ErrorConfig.unfound_modules))
  TypeNode.showstat()
  for module in modules:
    print '===', module.get_name(), '==='
    module.showrec(IndentedStream(sys.stdout))
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
