#!/usr/bin/env bash
# Build the Flow Launcher plugin archive and print its path.
# Usage: scripts/package.sh [out_dir]   (default: dist)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
out_dir="${1:-$root/dist}"
version="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["Version"])' "$root/data/plugin.json")"
oldest_python="$(sed -n 's/^requires-python = ">=\([0-9.]*\)"/\1/p' "$root/pyproject.toml")"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT

cp "$root/run.py" "$root/LICENSE" "$build_dir/"
cp "$root/data/icon.png" "$root/data/plugin.json" "$root/data/SettingsTemplate.yaml" "$build_dir/"

site_dir="$build_dir/site-packages"
mkdir -p "$site_dir"
cp -r "$root/src/klipyboard" "$site_dir/"
find "$build_dir" -name __pycache__ -prune -exec rm -rf {} +

# Vendor the locked pure-Python wheels resolved for Windows and the oldest
# supported Python, so the archive works with whichever Python Flow Launcher
# is configured to use.
uv export --project "$root" --frozen --no-dev --no-emit-project --no-hashes --quiet \
  --output-file "$build_dir/requirements.txt"
uv pip install -r "$build_dir/requirements.txt" \
  --target "$site_dir" \
  --python-version "$oldest_python" --python-platform x86_64-pc-windows-msvc \
  --only-binary :all: --no-config --quiet
rm -rf "$build_dir/requirements.txt" "$site_dir/bin" "$site_dir/.lock"

mkdir -p "$out_dir"
zip_path="$(cd "$out_dir" && pwd)/klipyboard-${version}.zip"
rm -f "$zip_path"
(cd "$build_dir" && zip -qr "$zip_path" .)
echo "$zip_path"
