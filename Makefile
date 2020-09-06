all: rust python
release: rust-release python-release

python:
	cd python/ && $(MAKE)

python-release:
	cd python/ && $(MAKE) release

rust:
	cargo build --manifest-path=rust/Cargo.toml

rust-release:
	cargo build --release --manifest-path=rust/Cargo.toml

.PHONY: all python rust rust-release python-release
