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
echo "The agent will start automatically on the next boot."
echo "To start it immediately without rebooting, run:"
echo "  sudo launchctl load $LAUNCH_DAEMON_PLIST"
echo ""
echo "To uninstall, run:"
echo "  sudo launchctl unload $LAUNCH_DAEMON_PLIST"
echo "  sudo rm -rf $INSTALL_DIR"
echo "  sudo rm $LAUNCH_DAEMON_PLIST"
