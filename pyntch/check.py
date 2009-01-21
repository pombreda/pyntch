#!/usr/bin/env python

import sys
from typenode import TypeNode
from exception import ExceptionFrame, MustBeDefinedNode
from namespace import Namespace
from module import load_module

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
  modpath = sys.path[:]
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-p': modpath.extend(v.split(':'))
  TypeNode.debug = debug
  ExceptionFrame.debug = debug
  Namespace.debug = debug
  Namespace.modpath = modpath
  for fname in args:
    if fname.endswith('.py'):
      name = fname[:-3]
    else:
      name = fname
    print '===', name, '==='
    MustBeDefinedNode.reset()
    module = load_module(name, debug=debug, modpath=modpath)
    MustBeDefinedNode.check()
    module.showrec(sys.stdout)
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
