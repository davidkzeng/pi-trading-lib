all: rust python
release: rust-release

python:
	cd python/ && pipenv run flake8 --config .flake8
	cd python/ && pipenv run mypy -p pi_trading_lib

rust:
	cargo build --manifest-path=rust/Cargo.toml

rust-release:
	cargo build --release --manifest-path=rust/Cargo.toml

.PHONY: all python rust rust-release
