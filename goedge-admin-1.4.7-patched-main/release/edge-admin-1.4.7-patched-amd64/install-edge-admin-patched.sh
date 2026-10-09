#!/bin/bash
set -euo pipefail

TARGET_DIR="/usr/local/goedge/edge-admin"
SERVICE_NAME="edge-admin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR=""

usage() {
	cat <<'EOF'
Usage: ./install-edge-admin-patched.sh [--target PATH] [--service NAME]

Options:
  --target PATH    Target edge-admin install directory. Default: /usr/local/goedge/edge-admin
  --service NAME   systemd service name. Default: edge-admin
  -h, --help       Show this help message
EOF
}

log() {
	printf '[install] %s\n' "$*"
}

fail() {
	printf '[install][error] %s\n' "$*" >&2
	exit 1
}

require_root() {
	if [ "${EUID:-$(id -u)}" -ne 0 ]; then
		fail "please run as root"
	fi
}

parse_args() {
	while [ "$#" -gt 0 ]; do
		case "$1" in
			--target)
				[ "$#" -ge 2 ] || fail "--target requires a path"
				TARGET_DIR="$2"
				shift 2
				;;
			--service)
				[ "$#" -ge 2 ] || fail "--service requires a name"
				SERVICE_NAME="$2"
				shift 2
				;;
			-h|--help)
				usage
				exit 0
				;;
			*)
				fail "unknown argument: $1"
				;;
		esac
	done
}

check_arch() {
	local arch
	arch="$(uname -m)"
	case "$arch" in
		x86_64|amd64)
			;;
		*)
			fail "unsupported architecture: $arch; this package is amd64 only"
			;;
	esac
}

check_package() {
	[ -f "$SCRIPT_DIR/bin/edge-admin" ] || fail "missing package binary: $SCRIPT_DIR/bin/edge-admin"
	[ -d "$SCRIPT_DIR/web/views/@default" ] || fail "missing package views: $SCRIPT_DIR/web/views/@default"
	[ -f "$SCRIPT_DIR/configs/plus.cache.json" ] || fail "missing package plus cache: $SCRIPT_DIR/configs/plus.cache.json"
}

check_target() {
	[ -d "$TARGET_DIR" ] || fail "target directory not found: $TARGET_DIR"
	[ -d "$TARGET_DIR/bin" ] || fail "target bin directory not found: $TARGET_DIR/bin"
	[ -d "$TARGET_DIR/web/views" ] || fail "target web views directory not found: $TARGET_DIR/web/views"
	mkdir -p "$TARGET_DIR/configs"
}

backup_current() {
	local timestamp
	timestamp="$(date +%Y%m%d-%H%M%S)"
	BACKUP_DIR="$TARGET_DIR/.backup-patched-$timestamp"
	mkdir -p "$BACKUP_DIR/bin" "$BACKUP_DIR/web/views" "$BACKUP_DIR/configs"

	log "creating backup: $BACKUP_DIR"
	[ -f "$TARGET_DIR/bin/edge-admin" ] && cp -a "$TARGET_DIR/bin/edge-admin" "$BACKUP_DIR/bin/edge-admin"
	[ -d "$TARGET_DIR/web/views/@default" ] && cp -a "$TARGET_DIR/web/views/@default" "$BACKUP_DIR/web/views/@default"
	[ -f "$TARGET_DIR/configs/plus.cache.json" ] && cp -a "$TARGET_DIR/configs/plus.cache.json" "$BACKUP_DIR/configs/plus.cache.json"
}

install_binary() {
	log "installing patched binary"
	cp -a "$SCRIPT_DIR/bin/edge-admin" "$TARGET_DIR/bin/edge-admin"
	chmod 755 "$TARGET_DIR/bin/edge-admin"
}

install_views() {
	log "installing patched views"
	rm -rf "$TARGET_DIR/web/views/@default"
	cp -a "$SCRIPT_DIR/web/views/@default" "$TARGET_DIR/web/views/@default"
}

install_plus_cache() {
	log "writing commercial cache"
	cp -a "$SCRIPT_DIR/configs/plus.cache.json" "$TARGET_DIR/configs/plus.cache.json"
	chmod 644 "$TARGET_DIR/configs/plus.cache.json"
}

restart_service() {
	command -v systemctl >/dev/null 2>&1 || fail "systemctl not found"
	log "restarting service: $SERVICE_NAME"
	systemctl restart "$SERVICE_NAME"
	systemctl is-active --quiet "$SERVICE_NAME" || fail "service failed to start: $SERVICE_NAME"
}

main() {
	parse_args "$@"
	require_root
	check_arch
	check_package
	check_target
	backup_current
	install_binary
	install_views
	install_plus_cache
	restart_service

	log "install complete"
	log "backup saved at: $BACKUP_DIR"
}

main "$@"
