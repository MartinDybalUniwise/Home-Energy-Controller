#!/usr/bin/env bash
# Instalace Home Energy Controller na Raspberry Pi / Linux.
# Spouštět z kořene repozitáře:  sudo ./dev/hec/deploy/install.sh
set -euo pipefail

TARGET="${HEC_TARGET:-/opt/home-energy-controller}"
SERVICE_USER="${HEC_USER:-${SUDO_USER:-$USER}}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "Zdroj:     $SOURCE"
echo "Cíl:       $TARGET"
echo "Uživatel:  $SERVICE_USER"

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(f"Vyžaduje Python 3.11+, nalezen {sys.version.split()[0]}")
PY

mkdir -p "$TARGET"
if [ "$SOURCE" != "$TARGET" ]; then
  # Provozní data se nepřepisují – kopíruje se jen kód a konfigurace.
  rsync -a --exclude 'data/' --exclude 'logs/' --exclude 'history/' \
        --exclude '.git/' --exclude '.env' "$SOURCE/" "$TARGET/"
fi

python3 -m pip install --break-system-packages -r "$TARGET/requirements.txt" 2>/dev/null \
  || python3 -m pip install -r "$TARGET/requirements.txt"

python3 "$TARGET/dev/run.py" --init
chown -R "$SERVICE_USER": "$TARGET"

sed "s/%i/$SERVICE_USER/" "$TARGET/dev/hec/deploy/hec.service" > /etc/systemd/system/hec.service
systemctl daemon-reload
systemctl enable --now hec.service

echo
echo "Hotovo. Stav:    systemctl status hec"
echo "Logy:            journalctl -u hec -f"
echo "Rozhraní:        http://$(hostname -I | awk '{print $1}'):8080"
echo
echo "Doplňte tajemství do $TARGET/.env a restartujte:  systemctl restart hec"
