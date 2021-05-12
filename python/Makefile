all: python
release: python-release

python:
	../bin/pyenv flake8 --config .flake8
	../bin/pyenv mypy --config-file mypy.ini pi_trading_lib

python-release:
	../bin/pyenv flake8 --config .flake8
	../bin/pyenv mypy --config-file mypy.ini pi_trading_lib
	# poetry build (disabled since we release by copying all files and using poetry in prod)

.PHONY: all release python python-release
