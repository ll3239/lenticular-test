#!/usr/bin/env bash
# Start local preview server reachable from phone (same WiFi).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 scripts/generate_entryway_storage_box.py --all-styles 2>/dev/null || true

PORT="${PORT:-8766}"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [ -z "$IP" ]; then
  IP="127.0.0.1"
fi

echo ""
echo "=========================================="
echo "  3D preview server"
echo "=========================================="
echo "  Entryway 3D:  http://127.0.0.1:${PORT}/viewer/entryway.html"
echo "  Short URL:    http://127.0.0.1:${PORT}/viewer/"
echo "  Phone:     http://${IP}:${PORT}/viewer/entryway.html"
echo ""
echo "  Phone must be on the SAME WiFi as this computer."
echo "  If it does not load, allow port ${PORT} in your firewall."
echo "=========================================="
echo ""

exec python3 -m http.server "$PORT" --bind 0.0.0.0
