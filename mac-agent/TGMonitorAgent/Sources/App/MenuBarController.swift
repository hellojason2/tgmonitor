import SwiftUI

enum MenuBarStatus {
    case active
    case disabled
    case offline
    case error
}

struct MenuBarView: View {
    @Binding var status: MenuBarStatus
    var onDisableRequested: () -> Void
    var onQuitRequested: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Circle()
                    .fill(statusColor)
                    .frame(width: 8, height: 8)
                Text("System Font Manager")
                    .font(.system(size: 12))
                Spacer()
            }
            Divider()
            Button("Status: \(statusText)") { }
                .disabled(true)
                .font(.system(size: 12))
            Divider()
            Button("Disable...") {
                onDisableRequested()
            }
            .font(.system(size: 12))
            Divider()
            Button("Quit") {
                onQuitRequested()
            }
            .font(.system(size: 12))
        }
        .padding(8)
        .frame(width: 200)
    }

    private var statusColor: Color {
        switch status {
        case .active: return .green
        case .disabled: return .yellow
        case .offline: return .yellow
        case .error: return .red
        }
    }

    private var statusText: String {
        switch status {
        case .active: return "Active"
        case .disabled: return "Disabled"
        case .offline: return "Offline"
        case .error: return "Error"
        }
    }
}

struct PasswordPromptView: View {
    @Binding var isPresented: Bool
    var onVerify: (String) -> Void

    @State private var password = ""
    @State private var errorMessage = ""

    var body: some View {
        VStack(spacing: 16) {
            Text("Enter Admin Password")
                .font(.headline)
            SecureField("Password", text: $password)
                .textFieldStyle(.roundedBorder)
            if !errorMessage.isEmpty {
                Text(errorMessage)
                    .foregroundColor(.red)
                    .font(.caption)
            }
            HStack {
                Button("Cancel") { isPresented = false }
                Button("Verify") {
                    onVerify(password)
                    password = ""
                }
                .keyboardShortcut(.return)
            }
        }
        .padding(20)
        .frame(width: 300)
    }
}

@MainActor
class MenuBarController: NSObject {
    private var statusItem: NSStatusItem?
    var onDisableRequested: (() -> Void)?
    var onQuitRequested: (() -> Void)?
    private var currentStatus: MenuBarStatus = .active

    override init() {
        super.init()
        setupStatusItem()
    }

    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem?.button {
            updateStatusImage()
        }

        statusItem?.menu = createMenu()
    }

    private func createMenu() -> NSMenu {
        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "System Font Manager", action: nil, keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Status: Active", action: nil, keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Disable...", action: #selector(disableClicked), keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(quitClicked), keyEquivalent: "q"))
        return menu
    }

    @objc private func disableClicked() {
        showPasswordPrompt()
    }

    @objc private func quitClicked() {
        onQuitRequested?()
    }

    private func showPasswordPrompt() {
        let alert = NSAlert()
        alert.messageText = "Enter Admin Password"
        alert.informativeText = "Password required to disable monitoring"
        alert.alertStyle = .informational
        alert.addButton(withTitle: "Verify")
        alert.addButton(withTitle: "Cancel")

        let inputField = NSSecureTextField(frame: NSRect(x: 0, y: 0, width: 200, height: 24))
        alert.accessoryView = inputField

        let response = alert.runModal()
        if response == .alertFirstButtonReturn {
            let password = inputField.stringValue
            if KeychainService.verifyAdminPassword(password) {
                onDisableRequested?()
            } else {
                showError("Incorrect password")
            }
        }
    }

    private func showError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Error"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }

    func updateStatus(_ status: MenuBarStatus) {
        currentStatus = status
        updateStatusImage()
        if let menu = statusItem?.menu {
            menu.items[2].title = "Status: \(statusText(for: status))"
        }
    }

    private func updateStatusImage() {
        if let button = statusItem?.button {
            let color: NSColor
            switch currentStatus {
            case .active: color = .systemGreen
            case .disabled: color = .systemYellow
            case .offline: color = .systemYellow
            case .error: color = .systemRed
            }

            let image = NSImage(size: NSSize(width: 10, height: 10))
            image.lockFocus()
            color.setFill()
            NSBezierPath(ovalIn: NSRect(x: 0, y: 0, width: 10, height: 10)).fill()
            image.unlockFocus()
            button.image = image
        }
    }

    private func statusText(for status: MenuBarStatus) -> String {
        switch status {
        case .active: return "Active"
        case .disabled: return "Disabled"
        case .offline: return "Offline"
        case .error: return "Error"
        }
    }
}
