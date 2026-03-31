import Foundation
import AppKit
import ScreenCaptureKit

enum CapturePermissionStatus {
    case authorized
    case denied
    case unknown
}

@MainActor
class ScreenshotCapture: NSObject {
    private var captureTimer: Timer?
    private let interval: TimeInterval
    private let storage: LocalStorage
    private let uploadQueue: UploadQueue
    private let statusManager: StatusManager

    var onPermissionDenied: (() -> Void)?

    init(interval: TimeInterval = 300, storage: LocalStorage, uploadQueue: UploadQueue, statusManager: StatusManager) {
        self.interval = interval
        self.storage = storage
        self.uploadQueue = uploadQueue
        self.statusManager = statusManager
        super.init()
    }

    func start() {
        checkPermissionAndCapture()

        captureTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.checkPermissionAndCapture()
            }
        }
    }

    func stop() {
        captureTimer?.invalidate()
        captureTimer = nil
    }

    private func checkPermissionAndCapture() {
        let status = checkScreenRecordingPermission()

        switch status {
        case .authorized:
            Task {
                await captureAndUpload()
            }
        case .denied:
            statusManager.setPermissionRequired()
            onPermissionDenied?()
            logPermissionDenied()
        case .unknown:
            statusManager.setError("Screen recording permission unknown")
        }
    }

    private func checkScreenRecordingPermission() -> CapturePermissionStatus {
        let hasAccess = CGPreflightScreenCaptureAccess()
        return hasAccess ? .authorized : .denied
    }

    func requestPermission() {
        CGRequestScreenCaptureAccess()
    }

    private func captureAndUpload() async {
        do {
            let screenshot = try await captureScreen()
            await uploadQueue.enqueue(screenshot: screenshot)
            statusManager.setActive()
        } catch ScreenshotError.permissionDenied {
            statusManager.setPermissionRequired()
            onPermissionDenied?()
            logPermissionDenied()
        } catch {
            statusManager.setError(error.localizedDescription)
        }
    }

    private func captureScreen() async throws -> Screenshot {
        guard CGPreflightScreenCaptureAccess() else {
            throw ScreenshotError.permissionDenied
        }

        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)

        guard let display = content.displays.sorted(by: { $0.displayID < $1.displayID }).first else {
            throw ScreenshotError.noDisplayFound
        }

        let filter = SCContentFilter(display: display, excludingWindows: [])

        let config = SCStreamConfiguration()
        config.width = 1366
        config.height = 768
        config.pixelFormat = kCVPixelFormatType_32BGRA
        config.showsCursor = false
        config.capturesAudio = false

        let cgImage: CGImage
        do {
            cgImage = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        } catch {
            throw ScreenshotError.captureFailed(error.localizedDescription)
        }

        guard let cgImage = cgImage as CGImage? else {
            throw ScreenshotError.captureFailed("Nil CGImage returned")
        }

        guard cgImage.width > 0 && cgImage.height > 0 else {
            throw ScreenshotError.permissionDenied
        }

        let bitmapRep = NSBitmapImageRep(cgImage: cgImage)
        guard let jpegData = bitmapRep.representation(using: .jpeg, properties: [.compressionFactor: 0.85]) else {
            throw ScreenshotError.compressionFailed
        }

        let activeApp = NSWorkspace.shared.frontmostApplication
        let appName = activeApp?.localizedName
        let windowTitle = getFrontmostWindowTitle()

        let screenshot = try await storage.save(jpegData: jpegData, appName: appName, windowTitle: windowTitle)
        return screenshot
    }

    private func getFrontmostWindowTitle() -> String? {
        let options: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
        guard let windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else {
            return nil
        }

        let frontmostPID = NSWorkspace.shared.frontmostApplication?.processIdentifier

        for window in windowList {
            guard let ownerPID = window[kCGWindowOwnerPID as String] as? Int32,
                  ownerPID == frontmostPID,
                  let windowName = window[kCGWindowName as String] as? String,
                  !windowName.isEmpty else {
                continue
            }
            return windowName
        }
        return nil
    }

    private func logPermissionDenied() {
        let logDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
            .appendingPathComponent("TGMonitorAgent/logs")
        try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)

        let logFile = logDir.appendingPathComponent("permission_denied.log")
        let entry = "\(ISO8601DateFormatter().string(from: Date())): Screen recording permission denied\n"
        if let data = entry.data(using: .utf8) {
            try? data.write(to: logFile, options: .atomic)
        }
    }
}

@MainActor
class StatusManager: ObservableObject {
    enum Status {
        case active
        case offline
        case error(String)
        case permissionRequired
        case disabled
    }

    @Published var currentStatus: Status = .active

    func setActive() { currentStatus = .active }
    func setOffline() { currentStatus = .offline }
    func setError(_ msg: String) { currentStatus = .error(msg) }
    func setPermissionRequired() { currentStatus = .permissionRequired }
    func setDisabled() { currentStatus = .disabled }
}
