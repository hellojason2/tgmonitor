import AppKit
import SwiftUI

@MainActor
class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?
    private var screenshotCapture: ScreenshotCapture?
    private var uploadQueue: UploadQueue?
    private var networkMonitor: NetworkMonitor?
    private var localStorage: LocalStorage?
    private var statusManager: StatusManager?

    func applicationDidFinishLaunching(_ notification: Notification) {
        localStorage = LocalStorage()
        Task {
            await localStorage?.setupDirectories()
            try? await localStorage?.cleanupOldScreenshots()
        }

        statusManager = StatusManager()
        networkMonitor = NetworkMonitor()
        networkMonitor?.startMonitoring()

        uploadQueue = UploadQueue(storage: localStorage!, statusManager: statusManager!)
        Task {
            await uploadQueue?.resumePendingUploads()
        }

        if !UserDefaults.standard.bool(forKey: "hasCompletedSetup") {
            showSetupWindow()
            return
        }

        startMonitoring()
    }

    func applicationWillTerminate(_ notification: Notification) {
        screenshotCapture?.stop()
        networkMonitor?.stopMonitoring()
    }

    private func showSetupWindow() {
        let setupWindow = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 400, height: 200),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        setupWindow.title = "System Font Manager"
        setupWindow.center()

        let setupView = SetupView(onComplete: { [weak self] in
            UserDefaults.standard.set(true, forKey: "hasCompletedSetup")
            self?.startMonitoring()
            setupWindow.close()
        })
        setupWindow.contentView = NSHostingView(rootView: setupView)
        setupWindow.makeKeyAndOrderFront(nil)
    }

    private func startMonitoring() {
        guard let storage = localStorage, let queue = uploadQueue, let status = statusManager else { return }

        screenshotCapture = ScreenshotCapture(
            interval: 300,
            storage: storage,
            uploadQueue: queue,
            statusManager: status
        )
        screenshotCapture?.onPermissionDenied = { [weak self] in
            self?.menuBarController?.updateStatus(.permissionRequired)
        }
        screenshotCapture?.start()

        menuBarController = MenuBarController(statusManager: status)
        menuBarController?.onDisableRequested = { [weak self] in
            self?.handleDisableRequest()
        }
        menuBarController?.onQuitRequested = {
            NSApplication.shared.terminate(nil)
        }
    }

    private func handleDisableRequest() {
        screenshotCapture?.stop()
        menuBarController?.updateStatus(.disabled)
    }

    func enableMonitoring() {
        screenshotCapture?.start()
        menuBarController?.updateStatus(.active)
    }
}
