#!/usr/bin/env python
from distutils.core import setup
from pyntch import __version__

setup(name='pyntch',
      version=__version__,
      description='Examine Python code and detect possible errors',
      license='MIT/X',
      author='Yusuke Shinyama',
      author_email='yusuke at cs dot nyu dot edu',
      url='http://www.unixuser.org/~euske/python/pyntch/index.html',
      long_description='''Pyntch is a PYthoN Type CHecker. It detects possible runtime
errors before actually running a code. Pyntch examines a source
code statically and infers all possible types of variables,
attributes, function arguments, and return values of each function
or method. Then it detects possible errors caused by type
mismatch, attribute not found, or other types of exceptions raised
from each function. Unlike other Python code checkers (such as
Pychecker or Pyflakes), Pyntch does not check the style issues.''',
      packages=['pyntch'],
      package_data={ 'pyntch': ['stub/*.pyi'] },
      scripts=['tools/tchecker.py', 'tools/makestub.py'],
      keywords=['static code analysis', 'type checking', 'type inference'],
      )
