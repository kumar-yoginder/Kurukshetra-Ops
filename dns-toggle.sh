#!/bin/bash

# --- Kurukshetra DNS Toggle Utility ---

set -e
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE=${1:-}

if [ "$MODE" == "recovery" ]; then
    echo "🛠️  Entering RECOVERY MODE (Host-based DNS for Docker Pulls)..."
    
    # 1. Re-enable DNSStubListener in systemd-resolved
    sudo sed -i 's/DNSStubListener=no/DNSStubListener=yes/' /etc/systemd/resolved.conf
    
    # 2. Reset the resolv.conf symlink to the internal stub
    sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
    
    # 3. Force an immediate nameserver for current session
    echo "nameserver ${RECOVERY_DNS:-8.8.8.8}" | sudo tee /etc/resolv.conf
    
    # 4. Restart services
    sudo systemctl restart systemd-resolved
    sudo systemctl restart docker
    echo "✅ Success. You can now run 'docker compose up -d'."

elif [ "$MODE" == "battle" ]; then
    echo "⚔️  Entering BATTLE MODE (Freeing Port 53 for Pi-hole)..."
    
    # 1. Disable the Stub Listener to free Port 53
    sudo sed -i 's/DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf
    
    # 2. Point resolv.conf to the actual static file
    sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
    
    # 3. Restart services
    sudo systemctl restart systemd-resolved
    echo "✅ Port 53 is now free. Starting Pi-hole..."
    
    # 4. Start Docker Containers
    cd "$PROJECT_DIR" && ./deploy.sh

else
    echo "Usage: ./dns-toggle.sh [recovery|battle]"
    echo "  recovery: Frees up networking to pull images."
    echo "  battle  : Disables system DNS so Pi-hole can start."
fi
