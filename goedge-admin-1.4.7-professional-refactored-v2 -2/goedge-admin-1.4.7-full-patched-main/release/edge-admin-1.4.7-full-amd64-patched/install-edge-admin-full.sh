#!/bin/bash
set -euo pipefail

TARGET_DIR="/usr/local/goedge/edge-admin"
SERVICE_NAME="edge-admin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$SCRIPT_DIR/edge-admin"
BACKUP_DIR=""

usage() {
	cat <<'EOF'
Usage: ./install-edge-admin-full.sh [--target PATH] [--service NAME]

Options:
  --target PATH    Target install directory. Default: /usr/local/goedge/edge-admin
  --service NAME   systemd service name. Default: edge-admin
  -h, --help       Show this help message
EOF
}

log() {
	printf '[install-full] %s\n' "$*"
}

fail() {
	printf '[install-full][error] %s\n' "$*" >&2
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
	[ -d "$PACKAGE_DIR" ] || fail "missing package dir: $PACKAGE_DIR"
	[ -f "$PACKAGE_DIR/bin/edge-admin" ] || fail "missing package binary"
	[ -d "$PACKAGE_DIR/web/public" ] || fail "missing web public assets"
	[ -d "$PACKAGE_DIR/web/views/@default" ] || fail "missing patched views"
	[ -f "$PACKAGE_DIR/edge-api/bin/edge-api" ] || fail "missing edge-api binary"
	[ -f "$PACKAGE_DIR/configs/server.template.yaml" ] || fail "missing server template"
	[ -f "$PACKAGE_DIR/configs/plus.cache.json" ] || fail "missing plus cache"
}

prepare_target() {
	mkdir -p "$TARGET_DIR"
}

backup_existing() {
	if [ ! -e "$TARGET_DIR/bin" ] && [ ! -e "$TARGET_DIR/web" ] && [ ! -e "$TARGET_DIR/edge-api" ] && [ ! -e "$TARGET_DIR/configs" ]; then
		return
	fi

	local timestamp
	timestamp="$(date +%Y%m%d-%H%M%S)"
	BACKUP_DIR="$TARGET_DIR/.backup-full-$timestamp"
	mkdir -p "$BACKUP_DIR"

	log "creating backup: $BACKUP_DIR"
	[ -e "$TARGET_DIR/bin" ] && cp -a "$TARGET_DIR/bin" "$BACKUP_DIR/bin"
	[ -e "$TARGET_DIR/web" ] && cp -a "$TARGET_DIR/web" "$BACKUP_DIR/web"
	[ -e "$TARGET_DIR/edge-api" ] && cp -a "$TARGET_DIR/edge-api" "$BACKUP_DIR/edge-api"
	[ -e "$TARGET_DIR/configs" ] && cp -a "$TARGET_DIR/configs" "$BACKUP_DIR/configs"
}

install_tree() {
	log "installing files to: $TARGET_DIR"
	mkdir -p "$TARGET_DIR"
	rm -rf "$TARGET_DIR/web/views/@default"
	cp -a "$PACKAGE_DIR/." "$TARGET_DIR/"
	chmod 755 "$TARGET_DIR/bin/edge-admin" "$TARGET_DIR/edge-api/bin/edge-api"
	mkdir -p "$TARGET_DIR/logs" "$TARGET_DIR/edge-api/logs" "$TARGET_DIR/edge-api/data"

	if [ ! -f "$TARGET_DIR/configs/server.yaml" ]; then
		cp -a "$TARGET_DIR/configs/server.template.yaml" "$TARGET_DIR/configs/server.yaml"
		log "created default server config: $TARGET_DIR/configs/server.yaml"
	fi
}

install_service() {
	local unit_path
	unit_path="/etc/systemd/system/${SERVICE_NAME}.service"

	command -v systemctl >/dev/null 2>&1 || fail "systemctl not found"

	cat >"$unit_path" <<EOF
[Unit]
Description=GoEdge Admin
After=network.target

[Service]
Type=forking
User=root
Group=root
WorkingDirectory=$TARGET_DIR
ExecStart=$TARGET_DIR/bin/edge-admin start
ExecStop=$TARGET_DIR/bin/edge-admin stop
ExecReload=$TARGET_DIR/bin/edge-admin restart
Restart=on-failure
RestartSec=5
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

	log "installing systemd service: $unit_path"
	systemctl daemon-reload
	systemctl enable "$SERVICE_NAME" >/dev/null
	systemctl restart "$SERVICE_NAME"
	systemctl is-active --quiet "$SERVICE_NAME" || fail "service failed to start: $SERVICE_NAME"
}

main() {
	parse_args "$@"
	require_root
	check_arch
	check_package
	prepare_target
	backup_existing
	install_tree
	install_service

	log "install complete"
	[ -n "$BACKUP_DIR" ] && log "backup saved at: $BACKUP_DIR"
	log "next step: open http://YOUR_SERVER_IP:7788/ and finish the web setup wizard"
}

main "$@"
