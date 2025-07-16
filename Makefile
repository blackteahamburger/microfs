XARGS := xargs -0 $(shell test $$(uname) = Linux && echo -r)
GREP_T_FLAG := $(shell test $$(uname) = Linux && echo -T)

all:
	@echo "\nThere is no default Makefile target right now. Try:\n"
	@echo "make clean - reset the project and remove auto-generated assets."
	@echo "make ruff - run the Ruff linter."
	@echo "make fix - run the Ruff linter and fix any issues it can."
	@echo "make test - run the test suite."
	@echo "make coverage - view a report on test coverage."
	@echo "make format_check - run the Ruff formatter to check for formatting issues."
	@echo "make format - run the Ruff formatter."
	@echo "make check - run all the checkers and tests."
	@echo "make docs - run sphinx to create project documentation.\n"

clean:
	rm -rf build
	rm -rf dist
	rm -rf microfs.egg-info
	rm -rf .coverage
	rm -rf docs/_build
	find . \( -name '*.py[co]' -o -name dropin.cache \) -print0 | $(XARGS) rm
	find . \( -name '*.bak' -o -name dropin.cache \) -print0 | $(XARGS) rm
	find . \( -name '*.tgz' -o -name dropin.cache \) -print0 | $(XARGS) rm

ruff:
	ruff check

fix:
	ruff check --fix

test: clean
	py.test

coverage: clean
	py.test --cov-report term-missing --cov=microfs tests/

format:
	ruff format

format_check:
	ruff format --check

check: clean ruff format_check coverage

docs: clean
	$(MAKE) -C docs html
	@echo "\nDocumentation can be found here:"
	@echo file://`pwd`/docs/_build/html/index.html
	@echo "\n"
