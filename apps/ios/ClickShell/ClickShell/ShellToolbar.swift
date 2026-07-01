import SwiftUI

struct ReaderShellView: View {
    @ObservedObject var store: ConnectionStore
    let baseURL: URL

    @State private var currentURL: URL
    @State private var reloadToken = UUID()
    @State private var showMenu = false
    @State private var loadError: String?

    init(store: ConnectionStore, baseURL: URL) {
        self.store = store
        self.baseURL = baseURL
        _currentURL = State(initialValue: store.homeURL(for: baseURL))
    }

    var body: some View {
        ZStack(alignment: .topTrailing) {
            ReaderWebView(url: $currentURL, reloadToken: $reloadToken, loadError: $loadError)
                .ignoresSafeArea()

            if let loadError {
                Text(loadError)
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(.white)
                    .padding(14)
                    .background(Color.black.opacity(0.74), in: RoundedRectangle(cornerRadius: 8))
                    .padding(.top, 72)
                    .padding(.horizontal, 16)
                    .frame(maxWidth: .infinity, alignment: .center)
            }

            Button {
                withAnimation(.easeOut(duration: 0.18)) {
                    showMenu.toggle()
                }
            } label: {
                Image(systemName: "ellipsis.circle.fill")
                    .font(.system(size: 28, weight: .semibold))
                    .symbolRenderingMode(.hierarchical)
                    .foregroundStyle(.white)
                    .padding(10)
                    .background(Color.black.opacity(0.38), in: Circle())
            }
            .buttonStyle(.plain)
            .padding(.top, 14)
            .padding(.trailing, 14)

            if showMenu {
                ShellToolbar(
                    connectionText: baseURL.host ?? "Mac",
                    goHome: {
                        currentURL = store.homeURL(for: baseURL)
                        showMenu = false
                    },
                    goLibrary: {
                        currentURL = store.libraryURL(for: baseURL)
                        showMenu = false
                    },
                    goRecordings: {
                        currentURL = store.recordingsURL(for: baseURL)
                        showMenu = false
                    },
                    goHermes: {
                        currentURL = store.hermesURL(for: baseURL)
                        showMenu = false
                    },
                    reload: {
                        reloadToken = UUID()
                        showMenu = false
                    },
                    changeAddress: {
                        store.resetConnection()
                    }
                )
                .padding(.top, 64)
                .padding(.trailing, 14)
            }
        }
    }
}

struct ShellToolbar: View {
    let connectionText: String
    let goHome: () -> Void
    let goLibrary: () -> Void
    let goRecordings: () -> Void
    let goHermes: () -> Void
    let reload: () -> Void
    let changeAddress: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(connectionText, systemImage: "wifi")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white.opacity(0.72))

            Button(action: goHome) {
                Label("首页", systemImage: "house")
            }
            Button(action: goLibrary) {
                Label("阅读", systemImage: "books.vertical")
            }
            Button(action: goRecordings) {
                Label("录音", systemImage: "waveform")
            }
            Button(action: goHermes) {
                Label("Hermes", systemImage: "message")
            }
            Button(action: reload) {
                Label("刷新", systemImage: "arrow.clockwise")
            }
            Button(role: .destructive, action: changeAddress) {
                Label("更换地址", systemImage: "network")
            }
        }
        .font(.callout.weight(.semibold))
        .foregroundStyle(.white)
        .buttonStyle(.plain)
        .padding(14)
        .frame(width: 188, alignment: .leading)
        .background(Color.black.opacity(0.78), in: RoundedRectangle(cornerRadius: 10))
    }
}
