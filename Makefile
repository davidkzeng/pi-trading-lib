all: rust python
release: rust-release

python:
	bin/pyenv flake8 --config python/.flake8
	bin/pyenv mypy python/pi_trading_lib

rust:
	cargo build --manifest-path=rust/Cargo.toml

rust-release:
	cargo build --release --manifest-path=rust/Cargo.toml

.PHONY: all python rust rust-release
