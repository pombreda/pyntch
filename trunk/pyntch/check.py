#!/usr/bin/env python

import sys
from frame import ExceptionRaiser
from module import load_module


# TODO:
#  hierarchical types (to handle exception catching)
#  hierarchical packages
#  builtin functions
#  builtin type methods
#  +=
#  __add__ etc.
#  automatic coercion

# main
def main(argv):
  import getopt
  def usage():
    print 'usage: %s [-d] [file ...]' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'd')
  except getopt.GetoptError:
    return usage()
  debug = 0
  for (k, v) in opts:
    if k == '-d': debug += 1
  for name in args:
    ExceptionRaiser.reset()
    module = load_module(name, '__main__', debug=debug)
    ExceptionRaiser.runall()
    module.showrec(sys.stdout)
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
