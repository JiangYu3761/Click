import SwiftUI
import WebKit

struct ReaderWebView: UIViewRepresentable {
    @Binding var url: URL
    @Binding var reloadToken: UUID
    @Binding var loadError: String?

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.isOpaque = false
        webView.backgroundColor = .black
        webView.scrollView.backgroundColor = .black
        webView.load(URLRequest(url: url))
        context.coordinator.lastURL = url
        context.coordinator.lastReloadToken = reloadToken
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        if context.coordinator.lastURL != url {
            webView.load(URLRequest(url: url))
            context.coordinator.lastURL = url
            context.coordinator.lastReloadToken = reloadToken
            return
        }
        if context.coordinator.lastReloadToken != reloadToken {
            webView.reload()
            context.coordinator.lastReloadToken = reloadToken
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        var parent: ReaderWebView
        var lastURL: URL?
        var lastReloadToken: UUID?

        init(_ parent: ReaderWebView) {
            self.parent = parent
        }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            parent.loadError = nil
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            parent.loadError = "页面加载失败，请检查 Mac 服务和网络。"
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            parent.loadError = "页面加载失败，请检查 Mac 服务和网络。"
        }
    }
}
