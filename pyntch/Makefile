# Makefile for pyntch

PACKAGE=pyntch

SVN=svn
GNUTAR=tar
PYTHON=python
TMPDIR=/tmp
VERSION=`$(PYTHON) $(PACKAGE)/__init__.py`
DISTNAME=$(PACKAGE)-dist-$(VERSION)
DISTFILE=$(DISTNAME).tar.gz

TCHECKER=$(PYTHON) tools/tchecker.py

all:

install:
	$(PYTHON) setup.py install

clean:
	-rm -rf build
	-cd $(PACKAGE) && $(MAKE) clean
	-cd tools && $(MAKE) clean
	-cd samples && $(MAKE) clean

testall:
	cd test && $(MAKE) test

# Maintainance:
commit: clean
	$(SVN) commit

check:
	cd $(PACKAGE) && make check

dist: clean
	$(SVN) cleanup
	$(SVN) export . $(TMPDIR)/$(DISTNAME)
	$(GNUTAR) c -z -C$(TMPDIR) -f $(TMPDIR)/$(DISTFILE) $(DISTNAME) --dereference --numeric-owner
	-rm -rf $(TMPDIR)/$(DISTNAME)

WEBDIR=$$HOME/Site/unixuser.org/python/pyntch
publish: dist
	cp $(TMPDIR)/$(DISTFILE) $(WEBDIR)
	cp README.html $(WEBDIR)/index.html
