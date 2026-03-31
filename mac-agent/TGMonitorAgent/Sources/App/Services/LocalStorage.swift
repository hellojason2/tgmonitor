import Foundation

class LocalStorage {
    private let fileManager = FileManager.default

    var screenshotsDirectory: URL {
        let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return appSupport.appendingPathComponent("TGMonitor/Screenshots")
    }

    func setupDirectories() {
        try? fileManager.createDirectory(at: screenshotsDirectory, withIntermediateDirectories: true)
    }

    func screenshotsDirectoryPath() -> URL {
        return screenshotsDirectory
    }
}
