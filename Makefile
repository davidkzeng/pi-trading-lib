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

rust-push-binary-python: rust-release
	find rust/target/release -maxdepth 1 -type f | grep -v "\." | xargs -I {} cp {} python/pi_trading_lib/rust_bin/

.PHONY: all python rust rust-release python-release
