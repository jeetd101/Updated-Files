#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKAGE_NAME="edge-admin-1.4.7-full-amd64-patched"
RELEASE_DIR="$REPO_ROOT/release/$PACKAGE_NAME"
DIST_DIR="$REPO_ROOT/dist"
ARCHIVE_PATH="$DIST_DIR/$PACKAGE_NAME.tar.gz"
SHA256_FILE="$DIST_DIR/SHA256SUMS"

sha256_cmd() {
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum "$1"
	elif command -v shasum >/dev/null 2>&1; then
		shasum -a 256 "$1"
	else
		printf 'missing sha256 tool\n' >&2
		exit 1
	fi
}

require_release() {
	[ -d "$RELEASE_DIR" ] || {
		printf 'missing release directory: %s\n' "$RELEASE_DIR" >&2
		exit 1
	}
	[ -f "$RELEASE_DIR/install-edge-admin-full.sh" ] || {
		printf 'missing install script: %s\n' "$RELEASE_DIR/install-edge-admin-full.sh" >&2
		exit 1
	}
	[ -f "$RELEASE_DIR/edge-admin/bin/edge-admin" ] || {
		printf 'missing edge-admin binary\n' >&2
		exit 1
	}
	[ -d "$RELEASE_DIR/edge-admin/web/public" ] || {
		printf 'missing web public directory\n' >&2
		exit 1
	}
	[ -d "$RELEASE_DIR/edge-admin/web/views/@default" ] || {
		printf 'missing web views directory\n' >&2
		exit 1
	}
	[ -f "$RELEASE_DIR/edge-admin/edge-api/bin/edge-api" ] || {
		printf 'missing edge-api binary\n' >&2
		exit 1
	}
}

main() {
	require_release
	mkdir -p "$DIST_DIR"
	rm -f "$ARCHIVE_PATH" "$SHA256_FILE"

	tar -czf "$ARCHIVE_PATH" -C "$REPO_ROOT/release" "$PACKAGE_NAME"
	(
		cd "$DIST_DIR"
		sha256_cmd "$PACKAGE_NAME.tar.gz" >"$SHA256_FILE"
	)

	printf 'archive: %s\n' "$ARCHIVE_PATH"
	printf 'sha256: %s\n' "$SHA256_FILE"
}

main "$@"
