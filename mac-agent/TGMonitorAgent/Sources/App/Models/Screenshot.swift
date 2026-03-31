import Foundation

struct Screenshot: Codable {
    let id: UUID
    let timestamp: Date
    let filePath: URL
    let analysisResult: String?
    let isFlagged: Bool

    init(filePath: URL) {
        self.id = UUID()
        self.timestamp = Date()
        self.filePath = filePath
        self.analysisResult = nil
        self.isFlagged = false
    }
}
