import Foundation

struct Screenshot: Codable, Sendable {
    let id: UUID
    let localPath: String
    let capturedAt: Date
    var uploaded: Bool
    var appName: String?
    var windowTitle: String?

    init(id: UUID = UUID(), localPath: String, capturedAt: Date = Date(), uploaded: Bool = false, appName: String? = nil, windowTitle: String? = nil) {
        self.id = id
        self.localPath = localPath
        self.capturedAt = capturedAt
        self.uploaded = uploaded
        self.appName = appName
        self.windowTitle = windowTitle
    }

    mutating func markUploaded() {
        uploaded = true
    }
}

enum ScreenshotError: Error, LocalizedError {
    case permissionDenied
    case compressionFailed
    case captureFailed(String)
    case noDisplayFound

    var errorDescription: String? {
        switch self {
        case .permissionDenied:
            return "Screen recording permission denied"
        case .compressionFailed:
            return "Failed to compress screenshot to JPEG"
        case .captureFailed(let reason):
            return "Screenshot capture failed: \(reason)"
        case .noDisplayFound:
            return "No display found for capture"
        }
    }
}
