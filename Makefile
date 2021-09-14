all: rust python create-py-bin
release: rust-release python-release create-py-bin
test: all rust-test python-test

create-py-bin:
	bin/create_py_exe analyze_results data_util archive md_visualize lj sim

include python/Makefile
include rust/Makefile

.PHONY: all release test
