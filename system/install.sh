#!/bin/bash

# WiFi Extender service installation script

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Create required directories
mkdir -p /etc/wifi-extender
mkdir -p /var/run/wifi-extender
mkdir -p /var/log/wifi-extender

# Set proper permissions
chown -R root:root /etc/wifi-extender
chmod 755 /etc/wifi-extender
chown -R root:root /var/run/wifi-extender
chmod 755 /var/run/wifi-extender
chown -R root:root /var/log/wifi-extender
chmod 755 /var/log/wifi-extender

# Install service control script
cp wifi-extender-service /usr/local/bin/
chmod 755 /usr/local/bin/wifi-extender-service

# Install systemd service
cp wifi-extender.service /etc/systemd/system/
chmod 644 /etc/systemd/system/wifi-extender.service

# Create default configuration
if [ ! -f /etc/wifi-extender/config.json ]; then
    cat > /etc/wifi-extender/config.json << EOL
{
    "upstream": {
        "ssid": "",
        "password": ""
    },
    "ap": {
        "ssid": "WiFi-Extender",
        "password": "",
        "channel": 6
    }
}
EOL
    chmod 600 /etc/wifi-extender/config.json
fi

# Reload systemd
systemctl daemon-reload

echo "WiFi Extender service installed successfully"
echo "Edit /etc/wifi-extender/config.json to configure your networks"
echo "Then start the service with: systemctl start wifi-extender"
echo "Enable at boot with: systemctl enable wifi-extender" 