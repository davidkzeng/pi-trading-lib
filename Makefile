all: rust python
release: rust-release python-release
test: all rust-test python-test

include python/Makefile
include rust/Makefile

.PHONY: all release test
