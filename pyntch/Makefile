# Makefile for pyntch

PACKAGE=pyntch

SVN=svn
GNUTAR=tar
PYTHON=python
TMPDIR=/tmp
VERSION=`$(PYTHON) $(PACKAGE)/__init__.py`
DISTNAME=$(PACKAGE)-dist-$(VERSION)
DISTFILE=$(DISTNAME).tar.gz
PREFIX=/usr/local

TCHECKER=tools/tchecker.py

all:

install:
	$(PYTHON) setup.py install --prefix=$(PREFIX)

selfcheck:
	PYTHONPATH=. $(PYTHON) $(TCHECKER) -t xml $(TCHECKER) > selfcheck.xml

clean:
	-rm -rf build selfcheck.xml
	-cd $(PACKAGE) && $(MAKE) clean
	-cd tools && $(MAKE) clean

check:
	cd test && $(MAKE) check

# Maintainance:
commit: clean
	$(SVN) commit

dist: clean
	$(SVN) cleanup
	$(SVN) export . $(TMPDIR)/$(DISTNAME)
	$(GNUTAR) c -z -C$(TMPDIR) -f $(TMPDIR)/$(DISTFILE) $(DISTNAME) --dereference --numeric-owner
	-rm -rf $(TMPDIR)/$(DISTNAME)

WEBDIR=$$HOME/Site/unixuser.org/python/pyntch
publish: dist
	cp $(TMPDIR)/$(DISTFILE) $(WEBDIR)/
	cp docs/index.html docs/*.png $(WEBDIR)/
