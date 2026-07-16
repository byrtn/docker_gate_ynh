#!/bin/bash

#=================================================
# COMMON VARIABLES
#=================================================

python_version="3.11"
venv_dir="$install_dir/venv"

#=================================================
# PERSONAL HELPERS
#=================================================

# Vérifie que Docker CE est installé et fonctionnel, l'installe sinon.
# Gère le piège iptables/nftables rencontré le 10/07/2026 (VM 203, incident Portainer) :
# après installation, on force un redémarrage du service pour reconstruire
# proprement les chaînes réseau si le système utilise nftables.
ynh_docker_gate__ensure_docker_installed() {
    if command -v docker >/dev/null 2>&1 && systemctl is-active --quiet docker; then
        ynh_print_info --message="Docker déjà installé et actif, rien à faire."
        return 0
    fi

    ynh_print_info --message="Installation de Docker CE..."

    ynh_apt update
    ynh_apt install --package="ca-certificates curl gnupg"

    install -m 0755 -d /etc/apt/keyrings
    if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
        curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
    fi

    local debian_codename
    debian_codename=$(. /etc/os-release && echo "$VERSION_CODENAME")

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $debian_codename stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null

    ynh_apt update
    ynh_apt install --package="docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"

    systemctl enable --now docker

    # Piège connu (10/07/2026) : si nftables était déjà actif avant l'installation
    # de Docker, les chaînes iptables créées au premier démarrage peuvent être
    # incohérentes. Un redémarrage propre du service les reconstruit correctement.
    systemctl restart docker

    if ! systemctl is-active --quiet docker; then
        ynh_die --message="Docker n'a pas pu démarrer correctement après installation."
    fi

    ynh_print_info --message="Docker CE installé et actif."
}
