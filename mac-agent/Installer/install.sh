#!/bin/bash
set -e

# TGMonitor Agent Install Script
# Must be run with admin privileges (sudo)
# This script installs the TGMonitor LaunchDaemon and app bundle

# Check if running with root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run with sudo or as root"
    exit 1
fi

INSTALL_DIR="/Library/com.jsr.systemhelper"
LAUNCH_DAEMON_DIR="/Library/LaunchDaemons"
LAUNCH_DAEMON_PLIST="$LAUNCH_DAEMON_DIR/com.jsr.tgmonitor.plist"
SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="/var/log/tgmonitor-install.log"

echo "TGMonitor Agent Installer"
echo "========================="

# Verify app bundle exists
if [ ! -d "$SOURCE_DIR/TGMonitorAgent/TGMonitorAgent.app" ]; then
    echo "Error: TGMonitorAgent.app not found in $SOURCE_DIR"
    echo "Please build the project first with: xcodebuild -scheme TGMonitorAgent -configuration Release"
    exit 1
fi

# Stop existing daemon if running
echo "Stopping existing daemon if running..."
launchctl unload "$LAUNCH_DAEMON_PLIST" 2>/dev/null || true

# Create install directory
echo "Creating install directory..."
mkdir -p "$INSTALL_DIR"

# Generate device token
echo "Generating device token..."
DEVICE_TOKEN=$(openssl rand -hex 32)
MACHINE_ID=$(scutil --get LocalHostName 2>/dev/null || echo "unknown-mac")

echo "Device token: $DEVICE_TOKEN"
echo "Machine ID: $MACHINE_ID"

# Log token for admin reference
echo "========================================" >> "$LOG_FILE"
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$LOG_FILE"
echo "Machine ID: $MACHINE_ID" >> "$LOG_FILE"
echo "Device Token: $DEVICE_TOKEN" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "IMPORTANT: Register this device on VPS before first upload." >> "$LOG_FILE"
echo "Run on VPS:" >> "$LOG_FILE"
echo "  echo -n '$DEVICE_TOKEN' | sha256sum | cut -d' ' -f1" >> "$LOG_FILE"
echo "Then insert into PostgreSQL:" >> "$LOG_FILE"
echo "  INSERT INTO devices (machine_id, token_hash, employee_id)" >> "$LOG_FILE"
echo "  VALUES ('$MACHINE_ID', 'SHA256_HASH', 'EMPLOYEE_UUID');" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo ""

# Store device token in Keychain
echo "Storing device token in Keychain..."
security add-generic-password \
    -s "com.jsr.systemhelper" \
    -a "device-token" \
    -w "$DEVICE_TOKEN" \
    -T "$INSTALL_DIR/TGMonitorAgent.app/Contents/MacOS/TGMonitorAgent" \
    2>/dev/null || security add-generic-password \
    -s "com.jsr.systemhelper" \
    -a "device-token" \
    -w "$DEVICE_TOKEN" \
    -T "$INSTALL_DIR/TGMonitorAgent.app/Contents/MacOS/TGMonitorAgent"

# Copy app bundle
echo "Copying app bundle..."
cp -R "$SOURCE_DIR/TGMonitorAgent/TGMonitorAgent.app" "$INSTALL_DIR/"

# Set ownership to root:wheel
echo "Setting ownership to root:wheel..."
chown -R root:wheel "$INSTALL_DIR/TGMonitorAgent.app"

# Set permissions
echo "Setting permissions..."
chmod 755 "$INSTALL_DIR/TGMonitorAgent.app"
chmod 755 "$INSTALL_DIR/TGMonitorAgent.app/Contents/MacOS/TGMonitorAgent"
chmod 644 "$INSTALL_DIR/TGMonitorAgent.app/Contents/Resources/Info.plist"
chmod 644 "$INSTALL_DIR/TGMonitorAgent.app/Contents/Resources/TGMonitorAgent.entitlements"

# Copy LaunchDaemon plist
echo "Installing LaunchDaemon plist..."
mkdir -p "$LAUNCH_DAEMON_DIR"
cp "$SOURCE_DIR/LaunchDaemon/com.jsr.tgmonitor.plist" "$LAUNCH_DAEMON_PLIST"
chown root:wheel "$LAUNCH_DAEMON_PLIST"
chmod 644 "$LAUNCH_DAEMON_PLIST"

echo ""
echo "Installation complete!"
echo ""
echo "The TGMonitor agent has been installed to: $INSTALL_DIR"
echo "LaunchDaemon plist installed to: $LAUNCH_DAEMON_PLIST"
echo ""
echo "IMPORTANT: See $LOG_FILE for device token and VPS registration instructions."
echo ""
echo "The agent will start automatically on the next boot."
echo "To start it immediately without rebooting, run:"
echo "  sudo launchctl load $LAUNCH_DAEMON_PLIST"
echo ""
echo "To uninstall, run:"
echo "  sudo launchctl unload $LAUNCH_DAEMON_PLIST"
echo "  sudo rm -rf $INSTALL_DIR"
echo "  sudo rm $LAUNCH_DAEMON_PLIST"
