#!/usr/bin/env python
from distutils.core import setup

setup(name='pyntch',
      version='20090531',
      description='Python source code analyzer',
      license='MIT/X',
      author='Yusuke Shinyama',
      url='http://www.unixuser.org/~euske/python/pyntch/index.html',
      packages=['pyntch'],
      package_data={ 'pyntch': ['stub/*.pyi'] },
      scripts=['tools/tchecker.py', 'tools/makestub.py'],
      )
