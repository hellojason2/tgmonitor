import Foundation
import Network

actor UploadQueue {
    private let storage: LocalStorage
    private let statusManager: StatusManager
    private let maxRetries = 5
    private let baseRetryInterval: TimeInterval = 60
    private var pendingUploads: [Screenshot] = []
    private var isUploading = false

    private let session: URLSession

    private var vpsEndpoint: String {
        return "http://72.62.148.50:8000"
    }

    /// Admin password used for device enrollment — must match server ADMIN_PASSWORD
    private var adminPassword: String {
        return "jsr_monitor_2026"
    }

    private var employeeId: String {
        let configURL = URL(fileURLWithPath: "/Library/com.jsr.systemhelper/config.json")
        guard let data = try? Data(contentsOf: configURL),
              let json = try? JSONDecoder().decode([String: String].self, from: data),
              let id = json["employee_id"] else {
            return "00000000-0000-0000-0000-000000000000"
        }
        return id
    }

    private var machineId: String {
        Host.current().localizedName ?? "unknown-mac"
    }

    init(storage: LocalStorage, statusManager: StatusManager) {
        self.storage = storage
        self.statusManager = statusManager
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
    }

    func enqueue(screenshot: Screenshot) {
        pendingUploads.append(screenshot)
        Task {
            await processQueue()
        }
    }

    func resumePendingUploads() {
        Task {
            await processQueue()
        }
    }

    private func processQueue() async {
        guard !isUploading, !pendingUploads.isEmpty else { return }
        isUploading = true

        for screenshot in pendingUploads {
            let success = await uploadWithRetry(screenshot)
            if success {
                pendingUploads.removeAll { $0.id == screenshot.id }
            }
        }
        isUploading = false
    }

    private func uploadWithRetry(_ screenshot: Screenshot) async -> Bool {
        var attempt = 0
        while attempt < maxRetries {
            do {
                try await upload(screenshot)
                return true
            } catch {
                attempt += 1
                let delay = baseRetryInterval * pow(2.0, Double(attempt - 1))
                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            }
        }
        return false
    }

    private func upload(_ screenshot: Screenshot) async throws {
        // Auto-register device if no token exists
        var token = KeychainService.getDeviceToken()
        if token == nil {
            print("[UploadQueue] No device token found — attempting auto-registration...")
            guard let registration = try? await registerDevice() else {
                throw UploadError.noToken
            }
            try KeychainService.setDeviceToken(registration.token)
            token = registration.token
            print("[UploadQueue] Device registered with ID: \(registration.deviceId)")
        }

        var request = URLRequest(url: URL(string: "\(vpsEndpoint)/api/v1/screenshots")!)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token ?? "")", forHTTPHeaderField: "Authorization")

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"employee_id\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(employeeId)\r\n".data(using: .utf8)!)

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"machine_id\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(machineId)\r\n".data(using: .utf8)!)

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"captured_at\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(screenshot.capturedAt.ISO8601Format())\r\n".data(using: .utf8)!)

        if let appName = screenshot.appName {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"app_name\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(appName)\r\n".data(using: .utf8)!)
        }

        if let windowTitle = screenshot.windowTitle {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"window_title\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(windowTitle)\r\n".data(using: .utf8)!)
        }

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(screenshot.id.uuidString).jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)

        let fileData = try await loadFileData(from: URL(fileURLWithPath: screenshot.localPath))
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (_, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw UploadError.serverRejected
        }
    }

    private func loadFileData(from url: URL) async throws -> Data {
        try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                do {
                    let data = try Data(contentsOf: url)
                    continuation.resume(returning: data)
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    private struct DeviceRegistration: Codable {
        let deviceId: String
        let token: String
        let employeeId: String
    }

    private func registerDevice() async throws -> DeviceRegistration {
        let machineName = Host.current().localizedName ?? "unknown-mac"

        var request = URLRequest(url: URL(string: "\(vpsEndpoint)/api/v1/devices/register")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ["name": machineName, "admin_password": adminPassword]
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw UploadError.serverRejected
        }

        return try JSONDecoder().decode(DeviceRegistration.self, from: data)
    }
}

enum UploadError: Error, LocalizedError {
    case noToken
    case serverRejected
    case networkUnavailable

    var errorDescription: String? {
        switch self {
        case .noToken:
            return "No device token found in Keychain"
        case .serverRejected:
            return "VPS server rejected the upload"
        case .networkUnavailable:
            return "Network is unavailable"
        }
    }
}
