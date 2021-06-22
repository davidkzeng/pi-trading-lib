all: rust python create-py-bin
release: rust-release python-release create-py-bin
test: all rust-test python-test

create-py-bin:
	bin/create_py_exe analyze_results create_py_exe data_util archive md_visualize lj

include python/Makefile
include rust/Makefile

.PHONY: all release test
