import Foundation

@MainActor
final class ConnectionStore: ObservableObject {
    @Published var hostInput: String
    @Published var portInput: String
    @Published var accessTokenInput: String
    @Published private(set) var connectedBaseURL: URL?
    @Published var statusMessage: String = ""
    @Published var isChecking = false

    private let defaults: UserDefaults
    private let hostKey = "ClickShell.hostInput.v1"
    private let portKey = "ClickShell.portInput.v1"
    private let accessTokenKey = "ClickShell.accessToken.v1"
    private let deviceIDKey = "ClickShell.deviceID.v1"
    private let baseURLKey = "ClickShell.connectedBaseURL.v1"
    private let homePath = "/home"
    private let libraryPath = "/library"
    private let recordingsPath = "/recordings"
    private let hermesPath = "/hermes"
    private let healthPath = "/health"

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        hostInput = defaults.string(forKey: hostKey) ?? ""
        portInput = defaults.string(forKey: portKey) ?? "18180"
        accessTokenInput = defaults.string(forKey: accessTokenKey) ?? ""
        if defaults.string(forKey: deviceIDKey) == nil {
            defaults.set("ios-\(UUID().uuidString)", forKey: deviceIDKey)
        }
    }

    var hasSavedAddress: Bool {
        !hostInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    func homeURL(for baseURL: URL) -> URL {
        urlWithAccess(path: homePath, baseURL: baseURL)
    }

    func libraryURL(for baseURL: URL) -> URL {
        urlWithAccess(path: libraryPath, baseURL: baseURL)
    }

    func recordingsURL(for baseURL: URL) -> URL {
        urlWithAccess(path: recordingsPath, baseURL: baseURL)
    }

    func hermesURL(for baseURL: URL) -> URL {
        urlWithAccess(path: hermesPath, baseURL: baseURL)
    }

    func healthURL(for baseURL: URL) -> URL {
        URL(string: healthPath, relativeTo: baseURL)?.absoluteURL ?? baseURL.appendingPathComponent("health")
    }

    func resetConnection() {
        connectedBaseURL = nil
        statusMessage = ""
    }

    func connect() async {
        guard let baseURL = normalizedBaseURL() else {
            statusMessage = "请输入 Mac 的局域网地址。"
            return
        }

        isChecking = true
        statusMessage = "正在连接 Click 服务..."
        defer { isChecking = false }

        var request = URLRequest(url: healthURL(for: baseURL))
        request.timeoutInterval = 5
        request.cachePolicy = .reloadIgnoringLocalAndRemoteCacheData

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                statusMessage = "没有连上 Click。请确认 Mac 已打开、同一 Wi-Fi、18180 正在运行。"
                return
            }
            connectedBaseURL = baseURL
            persist(baseURL: baseURL)
            statusMessage = "已连接"
        } catch {
            statusMessage = "连接失败。请确认 Mac 已打开、同一 Wi-Fi、18180 正在运行。"
        }
    }

    private func persist(baseURL: URL) {
        defaults.set(hostInput.trimmingCharacters(in: .whitespacesAndNewlines), forKey: hostKey)
        defaults.set(portInput.trimmingCharacters(in: .whitespacesAndNewlines), forKey: portKey)
        defaults.set(accessTokenInput.trimmingCharacters(in: .whitespacesAndNewlines), forKey: accessTokenKey)
        defaults.set(baseURL.absoluteString, forKey: baseURLKey)
    }

    var deviceID: String {
        if let existing = defaults.string(forKey: deviceIDKey), !existing.isEmpty {
            return existing
        }
        let created = "ios-\(UUID().uuidString)"
        defaults.set(created, forKey: deviceIDKey)
        return created
    }

    private func urlWithAccess(path: String, baseURL: URL) -> URL {
        let raw = URL(string: path, relativeTo: baseURL)?.absoluteURL ?? baseURL.appendingPathComponent(path.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
        guard var components = URLComponents(url: raw, resolvingAgainstBaseURL: false) else {
            return raw
        }
        var query = components.queryItems ?? []
        query.append(URLQueryItem(name: "device_id", value: deviceID))
        query.append(URLQueryItem(name: "device_name", value: "iPad Click"))
        let token = accessTokenInput.trimmingCharacters(in: .whitespacesAndNewlines)
        if !token.isEmpty {
            query.append(URLQueryItem(name: "access_token", value: token))
        }
        components.queryItems = query
        return components.url ?? raw
    }

    private func normalizedBaseURL() -> URL? {
        var raw = hostInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else {
            return nil
        }
        if !raw.contains("://") {
            raw = "http://\(raw)"
        }
        guard var components = URLComponents(string: raw) else {
            return nil
        }
        components.scheme = "http"
        components.path = ""
        components.query = nil
        components.fragment = nil
        if components.port == nil {
            let port = Int(portInput.trimmingCharacters(in: .whitespacesAndNewlines)) ?? 18180
            components.port = port
        }
        return components.url
    }
}
