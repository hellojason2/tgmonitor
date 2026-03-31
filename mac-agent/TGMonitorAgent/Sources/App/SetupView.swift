import SwiftUI

struct SetupView: View {
    var onComplete: () -> Void

    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var errorMessage = ""

    var body: some View {
        VStack(spacing: 20) {
            Text("System Font Manager Setup")
                .font(.headline)

            Text("Create an admin password to protect the monitoring settings.")
                .font(.caption)
                .multilineTextAlignment(.center)

            SecureField("Password", text: $password)
                .textFieldStyle(.roundedBorder)

            SecureField("Confirm Password", text: $confirmPassword)
                .textFieldStyle(.roundedBorder)

            if !errorMessage.isEmpty {
                Text(errorMessage)
                    .foregroundColor(.red)
                    .font(.caption)
            }

            Button("Continue") {
                setup()
            }
            .keyboardShortcut(.return)
            .disabled(password.isEmpty || confirmPassword.isEmpty)
        }
        .padding(30)
        .frame(width: 350)
    }

    private func setup() {
        guard password == confirmPassword else {
            errorMessage = "Passwords do not match"
            return
        }

        guard password.count >= 4 else {
            errorMessage = "Password must be at least 4 characters"
            return
        }

        do {
            try KeychainService.setAdminPasswordHash(password)
            onComplete()
        } catch {
            errorMessage = "Failed to save password"
        }
    }
}
