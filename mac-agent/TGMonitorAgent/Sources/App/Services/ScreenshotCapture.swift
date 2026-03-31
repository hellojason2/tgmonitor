import Foundation
import AppKit

@MainActor
class ScreenshotCapture {
    private var timer: Timer?
    private let interval: TimeInterval

    init(interval: TimeInterval = 300) {
        self.interval = interval
    }

    func start() {
        timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.capture()
            }
        }
        capture()
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    private func capture() {
        // Screenshot capture implemented in Plan 02-02
    }
}
