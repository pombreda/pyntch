# Makefile

PYTHON=python
CHECK=$(PYTHON) check.py

all:

clean:
	-rm *.pyc *.pyo
	cd pyntch && $(MAKE) clean
	cd stub && $(MAKE) clean
	cd test && $(MAKE) clean

testall: test/*.py
	$(CHECK) test/*.py
