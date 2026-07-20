#!/usr/bin/env bash
# verdict/install.sh — Universal installer
# Usage: curl -fsSL https://raw.githubusercontent.com/verdict/verdict-core/main/install.sh | bash

set -euo pipefail

REPO="verdict/verdict-core"
INSTALL_DIR="${VERDICT_INSTALL_DIR:-$HOME/.verdict/bin}"
VERSION="${VERDICT_VERSION:-latest}"
GITHUB_API="https://api.github.com/repos/${REPO}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
  x86_64) ARCH="amd64" ;;
  aarch64|arm64) ARCH="arm64" ;;
  *) log_error "Unsupported architecture: $ARCH"; exit 1 ;;
esac

case "$OS" in
  linux|darwin) ;;
  *) log_error "Unsupported OS: $OS"; exit 1 ;;
esac

# Get latest version if not specified
if [[ "$VERSION" == "latest" ]]; then
  log_info "Fetching latest release..."
  VERSION=$(curl -fsSL "${GITHUB_API}/releases/latest" | grep '"tag_name"' | sed -E 's/.*"tag_name": "([^"]+)".*/\1/')
  if [[ -z "$VERSION" ]]; then
    log_error "Failed to fetch latest version"
    exit 1
  fi
  log_info "Latest version: $VERSION"
fi

# Download and install
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

ASSET_NAME="verdict-${OS}-${ARCH}.tar.gz"
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${ASSET_NAME}"

log_info "Downloading $ASSET_NAME from $DOWNLOAD_URL..."
if ! curl -fsSL "$DOWNLOAD_URL" | tar -xz -C "$TMP_DIR"; then
  log_error "Download failed. Release may not exist for ${OS}/${ARCH}."
  log_info "Falling back to pipx install..."
  if command -v pipx >/dev/null 2>&1; then
    pipx install verdict-core
    log_success "Installed via pipx"
    exit 0
  else
    log_error "pipx not found. Please install pipx or download manually."
    exit 1
  fi
fi

mkdir -p "$INSTALL_DIR"
mv "$TMP_DIR/verdict" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/verdict"

log_success "verdict installed to $INSTALL_DIR"

# PATH guidance
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
  log_warn "Add $INSTALL_DIR to your PATH:"
  echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
  echo ""
  echo "  # For bash/zsh, add to ~/.bashrc or ~/.zshrc:"
  echo "  echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> ~/.bashrc"
  echo "  source ~/.bashrc"
fi

echo ""
log_success "Run: verdict route \"your task\""
