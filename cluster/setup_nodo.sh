#!/usr/bin/env bash
# setup_nodo.sh — Prepara UNA laptop (dentro de WSL2 Ubuntu 24.04). Correr en las 3.
# Uso:  bash setup_nodo.sh
set -euo pipefail

echo "== Paquetes =="
sudo apt-get update
sudo apt-get install -y openmpi-bin libopenmpi-dev openssh-server build-essential python3 iputils-ping

echo "== SSH en el puerto 2222 (el 22 puede chocar con el de Windows en modo espejo) =="
sudo sed -i 's/^#\?Port .*/Port 2222/' /etc/ssh/sshd_config
grep -q '^Port 2222' /etc/ssh/sshd_config || echo 'Port 2222' | sudo tee -a /etc/ssh/sshd_config >/dev/null
# Ubuntu 24.04 usa activacion por socket: la apagamos para que mande sshd_config
sudo systemctl disable --now ssh.socket 2>/dev/null || true
sudo systemctl enable --now ssh.service
sudo systemctl restart ssh.service

echo "== Llave SSH (sin contrasena) =="
mkdir -p ~/.ssh && chmod 700 ~/.ssh
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Puerto 2222 por defecto para las IPs del cluster (ajusta el rango si cambias la subred)
if ! grep -q '192.168.50.\*' ~/.ssh/config 2>/dev/null; then
cat >> ~/.ssh/config <<'EOF'
Host 192.168.50.*
    Port 2222
    StrictHostKeyChecking accept-new
    UserKnownHostsFile ~/.ssh/known_hosts
EOF
chmod 600 ~/.ssh/config
fi

mkdir -p ~/cluster
echo
echo "Listo en este nodo. Usuario: $(whoami)  (DEBE ser el mismo nombre en las 3 laptops)"
echo "Siguiente: copia la llave publica de abajo a las OTRAS laptops (authorized_keys):"
cat ~/.ssh/id_ed25519.pub
