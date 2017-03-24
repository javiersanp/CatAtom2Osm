SPHINXBUILD   = sphinx-build
COVERAGE      = coverage
DOCSRCDIR     = doc-src
BUILDDIR      = docs
COVERAGEDIR   = $(BUILDDIR)/coverage

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .
# the i18n builder cannot share the environment and doctrees with the others
I18NSPHINXOPTS  = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .

.PHONY: help
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html       to make standalone HTML files"

.PHONY: clean
clean:
	rm -rf $(BUILDDIR)/*

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

