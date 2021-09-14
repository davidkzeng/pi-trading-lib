rust:
	cargo build --manifest-path=rust/Cargo.toml

rust-release:
	cargo build --release --manifest-path=rust/Cargo.toml
	mkdir -p python/pi_trading_lib/rust_bin
	find rust/target/release -maxdepth 1 -type f | grep -v "\." | xargs -I {} cp {} python/pi_trading_lib/rust_bin/

rust-test:
	cargo test --manifest-path=rust/Cargo.toml

.PHONY: rust rust-release rust-test
