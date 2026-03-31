import Foundation
import Security
import CryptoKit

enum KeychainError: Error {
    case unableToStore
    case unableToRetrieve
    case unableToDelete
}

enum KeychainService {
    static let service = "com.jsr.systemhelper"
    static let passwordAccount = "admin-password-hash"

    /// Store SHA256 hash of admin password on first install
    /// Note: bcrypt requires swift-crypto SPM package. For v1, use SHA256 as a simpler
    /// alternative that still prevents plaintext storage. Upgrade to bcrypt via swift-crypto
    /// if stronger hashing is required.
    static func setAdminPasswordHash(_ password: String) throws {
        let hash = SHA256.hash(data: Data(password.utf8))
        let hashData = Data(hash)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: passwordAccount,
            kSecValueData as String: hashData
        ]

        // Delete existing item first
        SecItemDelete(query as CFDictionary)

        // Add new item
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainError.unableToStore
        }
    }

    /// Verify admin password against stored hash
    static func verifyAdminPassword(_ password: String) -> Bool {
        guard let storedHash = getAdminPasswordHash() else {
            return false
        }

        let inputHash = Data(SHA256.hash(data: Data(password.utf8)))
        return storedHash == inputHash
    }

    /// Retrieve stored admin password hash
    static func getAdminPasswordHash() -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: passwordAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess, let data = result as? Data else {
            return nil
        }

        return data
    }

    /// Delete stored admin password hash
    static func deleteAdminPasswordHash() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: passwordAccount
        ]

        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.unableToDelete
        }
    }

    /// Check if admin password has been set
    static func hasAdminPassword() -> Bool {
        return getAdminPasswordHash() != nil
    }

    // MARK: - Device Token (for VPS authentication)

    static let tokenAccount = "device-token"

    /// Store device token in Keychain
    static func setDeviceToken(_ token: String) throws {
        guard let data = token.data(using: .utf8) else { throw KeychainError.unableToStore }
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: tokenAccount,
            kSecValueData as String: data
        ]
        SecItemDelete(query as CFDictionary)
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else { throw KeychainError.unableToStore }
    }

    /// Retrieve device token from Keychain
    static func getDeviceToken() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: tokenAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess,
              let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            return nil
        }
        return token
    }
}
