import Foundation

actor LocalStorage {
    private let fileManager = FileManager.default
    private let baseDir: URL
    private let maxAgeDays = 30
    private let maxStorageBytes = 3 * 1024 * 1024 * 1024 // 3GB cap

    init() {
        let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        self.baseDir = appSupport.appendingPathComponent("TGMonitorAgent/screenshots")
    }

    func setupDirectories() {
        try? fileManager.createDirectory(at: baseDir, withIntermediateDirectories: true)
    }

    func screenshotsDirectory() -> URL {
        return baseDir
    }

    func save(jpegData: Data, appName: String? = nil, windowTitle: String? = nil) throws -> Screenshot {
        let now = Date()
        let id = UUID()

        let dateFormatter = ISO8601DateFormatter()
        dateFormatter.formatOptions = [.withFullDate]
        let dateStr = dateFormatter.string(from: now)

        let dir = baseDir.appendingPathComponent(dateStr)
        try fileManager.createDirectory(at: dir, withIntermediateDirectories: true)

        let filename = "\(id.uuidString).jpg"
        let fileURL = dir.appendingPathComponent(filename)
        try jpegData.write(to: fileURL)

        return Screenshot(
            id: id,
            localPath: fileURL.path,
            capturedAt: now,
            uploaded: false,
            appName: appName,
            windowTitle: windowTitle
        )
    }

    func markUploaded(_ screenshot: Screenshot) throws {
        // In a real implementation, update the screenshot's metadata
        // For now, the screenshot is tracked by its presence in the upload queue
    }

    func cleanupOldScreenshots() async throws {
        let cutoff = Calendar.current.date(byAdding: .day, value: -maxAgeDays, to: Date())!
        let enumerator = fileManager.enumerator(
            at: baseDir, includingPropertiesForKeys: [.contentModificationDateKey, .fileSizeKey]
        )

        var totalSize: Int64 = 0
        var filesToDelete: [URL] = []

        while let url = enumerator?.nextObject() as? URL {
            let resourceValues = try url.resourceValues(forKeys: [.contentModificationDateKey, .fileSizeKey])
            totalSize += Int64(resourceValues.fileSize ?? 0)

            if let modDate = resourceValues.contentModificationDate, modDate < cutoff {
                filesToDelete.append(url)
            }
        }

        for url in filesToDelete {
            try fileManager.removeItem(at: url)
        }

        if totalSize > maxStorageBytes {
            let allFiles = try collectAllFilesSortedByDate()
            for url in allFiles {
                guard totalSize > maxStorageBytes else { break }
                let size = Int64(try url.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0)
                try fileManager.removeItem(at: url)
                totalSize -= size
            }
        }
    }

    private func collectAllFilesSortedByDate() throws -> [URL] {
        let enumerator = fileManager.enumerator(
            at: baseDir, includingPropertiesForKeys: [.contentModificationDateKey]
        )
        var files: [URL] = []
        while let url = enumerator?.nextObject() as? URL {
            files.append(url)
        }
        return files.sorted { lhs, rhs in
            let lhsDate = (try? lhs.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? Date.distantPast
            let rhsDate = (try? rhs.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? Date.distantPast
            return lhsDate < rhsDate
        }
    }
}
