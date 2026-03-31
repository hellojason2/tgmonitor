import Foundation
import Network

class NetworkMonitor: @unchecked Sendable {
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "NetworkMonitor")

    private var _isConnected = false
    var isConnected: Bool {
        return _isConnected
    }

    func startMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            self?._isConnected = path.status == .satisfied
        }
        monitor.start(queue: queue)
    }

    func stopMonitoring() {
        monitor.cancel()
    }
}
