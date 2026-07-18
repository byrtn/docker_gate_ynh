#!/bin/bash

#=================================================
# COMMON VARIABLES
#=================================================

venv_dir="$install_dir/venv"

#=================================================
# PERSONAL HELPERS
#=================================================

# Checks that Docker CE is installed and functional, installs it otherwise.
# Handles the iptables/nftables trap encountered on 2026-07-10 (VM 203,
# Portainer incident): after installation, force a service restart to
# properly rebuild the network chains if the system uses nftables.
ynh_docker_gate__ensure_docker_installed() {
    if command -v docker >/dev/null 2>&1 && systemctl is-active --quiet docker; then
        ynh_print_info --message="Docker already installed and active, nothing to do."
        return 0
    fi

    ynh_print_info --message="Installing Docker CE..."

    ynh_apt update
    ynh_apt install ca-certificates curl gnupg

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
    ynh_apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    systemctl enable --now docker

    # Known trap (2026-07-10): if nftables was already active before installing
    # Docker, the iptables chains created on first startup can end up
    # inconsistent. A clean service restart rebuilds them correctly.
    systemctl restart docker

    if ! systemctl is-active --quiet docker; then
        ynh_die --message="Docker failed to start properly after installation."
    fi

    ynh_print_info --message="Docker CE installed and active."
}
