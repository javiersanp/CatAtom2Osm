SHELL         = /bin/bash
SPHINXBUILD   = sphinx-build
APIBUILD      = sphinx-apidoc
COVERAGE      = coverage
DOCSRCDIR     = doc-src
BUILDDIR      = docs
COVERAGEDIR   = $(BUILDDIR)/coverage
APIDIR        = $(DOCSRCDIR)/en/api
GETTEXT       = pygettext
MSGMERGE      = msgmerge
MSGFMT        = msgfmt
LOCALE_DIR    = locale/po
OS            = $(shell uname)

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .
# the i18n builder cannot share the environment and doctrees with the others
I18NSPHINXOPTS  = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .

.PHONY: help
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  clean      to clean docs build directory"
	@echo "  coverage   to make coverage report files"
	@echo "  api        to make autodoc files"
	@echo "  html       to make documentation html files"
	@echo "  msg        to build translations file"
	@echo "  install    to create application simbolic link"
	@echo "  all        clean api coverage html msg install"

.PHONY: clean
clean:
	rm -rf $(BUILDDIR)/*
	touch $(BUILDDIR)/.nojekyll

.PHONY: html
html:
	rm -rf $(DOCSRCDIR)/es/api/*.rst
	for f in $(DOCSRCDIR)/en/api/*.rst; do \
		echo ".. include:: ../../en/api/$$(basename $$f)" > "$(DOCSRCDIR)/es/api/$$(basename $$f)"; \
	done
	cd $(DOCSRCDIR) && make html

.PHONY: coverage
coverage:
	$(COVERAGE) run --source=. test/unittest_main.py discover
	$(COVERAGE) report
	$(COVERAGE) html
	@echo
	@echo "Coverage finished. The HTML pages are in $(COVERAGEDIR)."

.PHONY: api
api:
	$(APIBUILD) -f -e -o $(APIDIR) .
	@echo
	@echo "API autodoc finished. The HTML pages are in $(APIDIR)."

.PHONY: msg
msg:
	$(GETTEXT) -o $(LOCALE_DIR)/messages.pot *.py
	$(MSGMERGE) -U $(LOCALE_DIR)/es/LC_MESSAGES/catatom2osm.po $(LOCALE_DIR)/messages.pot
	$(MSGFMT) $(LOCALE_DIR)/es/LC_MESSAGES/catatom2osm.po -o $(LOCALE_DIR)/es/LC_MESSAGES/catatom2osm.mo
	@echo
	@echo "Translation finished. The language files are in $(LOCALE_DIR)."


.PHONY: install
install:
	@echo "#!/bin/bash" > catatom2osm.sh
ifeq (${OS},$(filter $(OS),Sierra Darwin))
	@echo "export PATH="'"'"/Applications/QGIS.app/Contents/MacOS/bin:$$"PATH'"' >> catatom2osm.sh
	@echo "export PYTHONPATH="'"'"/Applications/QGIS.app/Contents/Resources/python:$$"PYTHONPATH'"' >> catatom2osm.sh
endif
	@echo "python $(shell pwd)/main.py $$"'*' >> catatom2osm.sh
	@chmod +x catatom2osm.sh
	@ln -sf $(shell pwd)/catatom2osm.sh /usr/bin/catatom2osm

all: clean api coverage html msg install
.PHONY: all

