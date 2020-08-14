all: rust python
release: rust-release
.PHONY: all

python:
	flake8 python/ --config python/.flake8
	(cd python/ && mypy -p pi_trading_lib)
.PHONY: python

rust:
	cargo build --manifest-path=rust/Cargo.toml
.PHONY: rust

rust-release:
	cargo build --release --manifest-path=rust/Cargo.toml
.PHONY: rust
