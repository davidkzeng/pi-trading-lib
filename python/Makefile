all: python
release: python-release

python:
	../bin/pyenv flake8 --config .flake8
	../bin/pyenv mypy --config-file mypy.ini pi_trading_lib

python-release:
	poetry build

.PHONY: all release python python-release
