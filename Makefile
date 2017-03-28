SPHINXBUILD   = sphinx-build
APIBUILD      = sphinx-apidoc
COVERAGE      = coverage
DOCSRCDIR     = doc-src
BUILDDIR      = docs
COVERAGEDIR   = $(BUILDDIR)/coverage
APIDIR        = $(DOCSRCDIR)/api

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .
# the i18n builder cannot share the environment and doctrees with the others
I18NSPHINXOPTS  = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .

.PHONY: help
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  coverage   to make coverage report files"
	@echo "  api        to make autodoc files"
	@echo "  html       to make documentation html files"

.PHONY: clean
clean:
	rm -rf $(BUILDDIR)/*
	touch $(BUILDDIR)/.nojekyll

.PHONY: html
html:
	$(SPHINXBUILD) -b html $(DOCSRCDIR) $(BUILDDIR)
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)."

.PHONY: coverage
coverage:
	$(COVERAGE) run test/unittest_main.py discover
	$(COVERAGE) report
	$(COVERAGE) html
	@echo
	@echo "Coverage finished. The HTML pages are in $(COVERAGEDIR)."

.PHONY: api
api:
	$(APIBUILD) -f -e -o $(APIDIR) .
	@echo
	@echo "API autodoc finished. The HTML pages are in $(APIDIR)."

all: clean api coverage html
.PHONY: all
