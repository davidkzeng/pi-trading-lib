python:
	bin/pyenv flake8 --config python/.flake8
	bin/pyenv mypy --config-file python/mypy.ini python/pi_trading_lib

python-release: python

python-test:
	bin/python -m unittest discover -s python

.PHONY: python python-release
