import Foundation

struct CompanionCommand: Codable {
    let id: String
    let command: String
    let params: [String: String]?
}

struct CompanionResponse: Codable {
    let id: String
    let status: String
    let data: [String: String]?
    let error: String?
}

enum CompanionServer {
    static func handle(_ cmd: CompanionCommand) -> CompanionResponse {
        switch cmd.command {
        case "get_status":
            return CompanionResponse(id: cmd.id, status: "success", data: ["platform": "ios", "service": "companion"], error: nil)
        case "collect_logs":
            return CompanionResponse(id: cmd.id, status: "success", data: ["hint": "read syslog stream"], error: nil)
        case "inspect_filesystem":
            let path = cmd.params?["path"] ?? "/var/mobile/Containers/Data/Application"
            return CompanionResponse(id: cmd.id, status: "success", data: ["hint": "list files under \(path) via jailbreak helper or app extension"], error: nil)
        case "dump_app_data":
            let bundleId = cmd.params?["bundle_id"] ?? "unknown.bundle"
            return CompanionResponse(id: cmd.id, status: "success", data: ["hint": "archive data container for \(bundleId) via jailbreak helper"], error: nil)
        case "dump_keychain":
            return CompanionResponse(id: cmd.id, status: "success", data: ["hint": "run keychain-dumper or Security framework helper"], error: nil)
        case "launch_app":
            let bundleId = cmd.params?["bundle_id"] ?? "unknown.bundle"
            return CompanionResponse(id: cmd.id, status: "success", data: ["hint": "launch \(bundleId) via frontboard or simctl equivalent"], error: nil)
        case "configure_proxy":
            let host = cmd.params?["host"] ?? "127.0.0.1"
            let port = cmd.params?["port"] ?? "8080"
            return CompanionResponse(id: cmd.id, status: "success", data: ["hint": "configure Wi-Fi proxy to \(host):\(port) or install transparent redirect profile"], error: nil)
        case "clear_proxy":
            return CompanionResponse(id: cmd.id, status: "success", data: ["hint": "clear configured proxy settings"], error: nil)
        case "screenshot":
            return CompanionResponse(id: cmd.id, status: "success", data: ["hint": "capture a screenshot and return the file path or base64 payload"], error: nil)
        default:
            return CompanionResponse(id: cmd.id, status: "error", data: nil, error: "unknown command")
        }
    }
}
