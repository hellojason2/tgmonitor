import AppKit
import SwiftUI

@MainActor
class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?
    private var screenshotCapture: ScreenshotCapture?
    private var uploadQueue: UploadQueue?
    private var networkMonitor: NetworkMonitor?
    private var localStorage: LocalStorage?

    func applicationDidFinishLaunching(_ notification: Notification) {
        localStorage = LocalStorage()
        localStorage?.setupDirectories()

        networkMonitor = NetworkMonitor()
        networkMonitor?.startMonitoring()

        uploadQueue = UploadQueue()
        uploadQueue?.resumePendingUploads()

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
        screenshotCapture = ScreenshotCapture(interval: 300)
        screenshotCapture?.start()

        menuBarController = MenuBarController()
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
