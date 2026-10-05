PYTHON := .venv/bin/python
export PYTHONPATH := $(CURDIR)/scripts:$(CURDIR)/stubs

.PHONY: setup setup-all test smoke verify-results
setup:
	bash scripts/setup.sh --core
setup-all:
	bash scripts/setup.sh --all
test:
	$(PYTHON) -m unittest discover -s tests -v
smoke:
	$(PYTHON) scripts/environment.py
	$(PYTHON) -m unittest discover -s tests -p 'test_causal_xml.py' -v
verify-results:
	$(PYTHON) scripts/verify_results.py
