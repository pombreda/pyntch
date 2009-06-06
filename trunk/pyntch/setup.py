#!/usr/bin/env python
from distutils.core import setup

setup(name='pyntch',
      version='20090531',
      description='Python source code analyzer',
      license='MIT/X',
      author='Yusuke Shinyama',
      author_email='yusuke at cs dot nyu dot edu',
      url='http://www.unixuser.org/~euske/python/pyntch/index.html',
      long_description='''Pyntch is a Python source code analyzer. It can detect possible runtime
errors before actually running a Python code. Pyntch examines a
source code statically and infers all possible types of variables,
class attributes, function signatures, and return values of
each function or method. Then it detects possible errors caused
by type mismatch or other exceptions raised from each function. Unlike
other Python code checker (such as Pychecker or Pyflakes), Pyntch
does not check the style issues.''',
      packages=['pyntch'],
      package_data={ 'pyntch': ['stub/*.pyi'] },
      scripts=['tools/tchecker.py', 'tools/makestub.py'],
      )
