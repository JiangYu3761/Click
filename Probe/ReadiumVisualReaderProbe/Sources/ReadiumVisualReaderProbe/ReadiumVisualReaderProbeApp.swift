import ReadiumNavigator
import ReadiumShared
import ReadiumStreamer
import SwiftUI
import UIKit
import WebKit

private let bundledFixtureName = "default-fixture"

@main
struct ReadiumVisualReaderProbeApp: App {
    var body: some Scene {
        WindowGroup {
            ReaderProbeView()
        }
    }
}

struct ReaderProbeView: View {
    @State private var publication: Publication?
    @State private var loadingState = "Opening EPUB..."
    @State private var interactionStatus = "单击聚焦当前句 · 双击添加备注 · 右键/双指点按整句标红"
    @State private var noteEditorPresented = false
    @State private var selectedSentence = ""
    @State private var noteText = ""
    @State private var redHighlightCount = 0

    var body: some View {
        ZStack {
            SwiftUI.Color.black.ignoresSafeArea()

            VStack(spacing: 0) {
                header

                ZStack(alignment: .bottom) {
                    if let publication {
                        EPUBNavigatorView(
                            publication: publication,
                            interactionStatus: $interactionStatus,
                            noteEditorPresented: $noteEditorPresented,
                            selectedSentence: $selectedSentence,
                            redHighlightCount: $redHighlightCount
                        )
                        .background(SwiftUI.Color.black)
                    } else {
                        VStack(spacing: 12) {
                            ProgressView()
                                .tint(.white)
                            Text(loadingState)
                                .font(chineseFont(size: 14))
                                .foregroundStyle(.secondary)
                                .multilineTextAlignment(.center)
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(SwiftUI.Color.black)
                    }

                    interactionBar
                        .padding(.horizontal, 10)
                        .padding(.bottom, 8)
                }
            }
        }
        .preferredColorScheme(.dark)
        .sheet(isPresented: $noteEditorPresented) {
            noteEditor
        }
        .task {
            await openFixture()
        }
    }

    private var header: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(publication?.metadata.title ?? "Sentence Reader Probe")
                    .font(chineseFont(size: 14, weight: .semibold))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                Text("Readium · 黑底中文阅读 · 句子交互探针")
                    .font(chineseFont(size: 11))
                    .foregroundStyle(.white.opacity(0.62))
            }

            Spacer()

            Text(publication == nil ? "Loading" : "Opened")
                .font(chineseFont(size: 11, weight: .medium))
                .foregroundStyle(publication == nil ? SwiftUI.Color.yellow : SwiftUI.Color.green)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(publication == nil ? SwiftUI.Color.yellow.opacity(0.16) : SwiftUI.Color.green.opacity(0.16))
                .clipShape(RoundedRectangle(cornerRadius: 6))
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 6)
        .background(SwiftUI.Color.black)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(SwiftUI.Color.white.opacity(0.12))
                .frame(height: 1)
        }
    }

    private var interactionBar: some View {
        HStack(spacing: 10) {
            Text(interactionStatus)
                .lineLimit(1)
                .truncationMode(.tail)
            Spacer(minLength: 8)
            Text("红标 \(redHighlightCount)")
                .lineLimit(1)
        }
        .font(chineseFont(size: 11, weight: .medium))
        .foregroundStyle(.white.opacity(0.78))
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 8))
        .overlay {
            RoundedRectangle(cornerRadius: 8)
                .stroke(SwiftUI.Color.white.opacity(0.12), lineWidth: 1)
        }
    }

    private var noteEditor: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("添加备注")
                .font(chineseFont(size: 16, weight: .semibold))
            Text(selectedSentence.isEmpty ? "当前句子" : selectedSentence)
                .font(chineseFont(size: 14))
                .foregroundStyle(.secondary)
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(SwiftUI.Color(uiColor: .secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            TextEditor(text: $noteText)
                .font(chineseFont(size: 14))
                .frame(minHeight: 120)
                .overlay {
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(SwiftUI.Color.secondary.opacity(0.25), lineWidth: 1)
                }
            HStack {
                Spacer()
                Button("取消") {
                    noteEditorPresented = false
                }
                Button("保存") {
                    interactionStatus = noteText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                        ? "已打开备注，但没有写入内容"
                        : "已为当前句保存备注（V1 内存态）"
                    noteEditorPresented = false
                    noteText = ""
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .padding(18)
        .frame(width: 460)
    }

    private func chineseFont(size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .custom("Microsoft YaHei", size: size).weight(weight)
    }

    @MainActor
    private func openFixture() async {
        do {
            guard let path = ProcessInfo.processInfo.environment["SENTENCE_READER_EPUB_FIXTURE"]
                ?? Bundle.main.url(forResource: bundledFixtureName, withExtension: "epub")?.path
            else {
                throw PublicationLoaderError.missingBundledFixture
            }
            let opened = try await PublicationLoader().open(filePath: path)
            publication = opened
        } catch {
            loadingState = "Failed to open EPUB: \(error)"
        }
    }
}

struct EPUBNavigatorView: UIViewControllerRepresentable {
    let publication: Publication
    @Binding var interactionStatus: String
    @Binding var noteEditorPresented: Bool
    @Binding var selectedSentence: String
    @Binding var redHighlightCount: Int

    func makeCoordinator() -> Coordinator {
        Coordinator(
            interactionStatus: $interactionStatus,
            noteEditorPresented: $noteEditorPresented,
            selectedSentence: $selectedSentence,
            redHighlightCount: $redHighlightCount
        )
    }

    func makeUIViewController(context: Context) -> UIViewController {
        do {
            let darkBackground = ReadiumNavigator.Color(hex: "#000000")
            let lightText = ReadiumNavigator.Color(hex: "#F5F5F5")
            let yahei: FontFamily = "Microsoft YaHei"
            let config = EPUBNavigatorViewController.Configuration(
                preferences: EPUBPreferences(
                    backgroundColor: darkBackground,
                    fontFamily: yahei,
                    fontSize: 1.05,
                    lineHeight: 1.72,
                    pageMargins: 0.02,
                    paragraphIndent: 0,
                    paragraphSpacing: 0.45,
                    publisherStyles: false,
                    scroll: false,
                    textAlign: .start,
                    textColor: lightText,
                    theme: .dark
                ),
                defaults: EPUBDefaults(
                    columnCount: .auto,
                    lineHeight: 1.72,
                    pageMargins: 0.02,
                    publisherStyles: false,
                    scroll: false,
                    textAlign: .start
                ),
                contentInset: [
                    .compact: (top: 0, bottom: 0),
                    .regular: (top: 0, bottom: 0),
                ],
                fontFamilyDeclarations: [
                    CSSFontFamilyDeclaration(
                        fontFamily: yahei,
                        alternates: ["微软雅黑", "PingFang SC", "Heiti SC", "Helvetica Neue", "Arial", "sans-serif"]
                    ).eraseToAnyHTMLFontFamilyDeclaration()
                ],
                readiumCSSRSProperties: CSSRSProperties(
                    textColor: CSSHexColor("#F5F5F5"),
                    backgroundColor: CSSHexColor("#000000"),
                    baseFontFamily: ["Microsoft YaHei", "微软雅黑", "PingFang SC", "Heiti SC", "Helvetica Neue", "Arial", "sans-serif"],
                    baseLineHeight: .unitless(1.72),
                    sansTf: ["Microsoft YaHei", "微软雅黑", "PingFang SC", "Heiti SC", "Helvetica Neue", "Arial", "sans-serif"],
                    compFontFamily: ["Microsoft YaHei", "微软雅黑", "PingFang SC", "Heiti SC", "Helvetica Neue", "Arial", "sans-serif"],
                    overrides: [
                        "--SR__sentenceReader": "enabled"
                    ]
                ),
                debugState: false
            )
            let controller = try EPUBNavigatorViewController(
                publication: publication,
                initialLocation: preferredInitialLocation(for: publication),
                config: config
            )
            controller.delegate = context.coordinator
            controller.view.backgroundColor = UIColor.black
            return controller
        } catch {
            let controller = UIViewController()
            controller.view.backgroundColor = UIColor.black
            let label = UILabel()
            label.text = "Navigator failed: \(error)"
            label.textColor = .white
            label.font = UIFont(name: "Microsoft YaHei", size: 14)
                ?? UIFont(name: "微软雅黑", size: 14)
                ?? .systemFont(ofSize: 14)
            label.numberOfLines = 0
            label.textAlignment = .center
            label.translatesAutoresizingMaskIntoConstraints = false
            controller.view.addSubview(label)
            NSLayoutConstraint.activate([
                label.leadingAnchor.constraint(equalTo: controller.view.leadingAnchor, constant: 20),
                label.trailingAnchor.constraint(equalTo: controller.view.trailingAnchor, constant: -20),
                label.centerYAnchor.constraint(equalTo: controller.view.centerYAnchor),
            ])
            return controller
        }
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {}

    private func preferredInitialLocation(for publication: Publication) -> Locator? {
        let htmlLinks = publication.readingOrder.filter { link in
            let href = link.href.lowercased()
            return (link.mediaType?.isHTML ?? href.hasSuffix(".xhtml") || href.hasSuffix(".html"))
                && !link.rels.contains(.cover)
                && !href.contains("cover")
                && !href.contains("nav")
                && !href.contains("toc")
        }

        let preferred = htmlLinks.first { link in
            link.href.lowercased().contains("part0010")
        } ?? htmlLinks.dropFirst(min(9, htmlLinks.count)).first
            ?? htmlLinks.first

        guard let link = preferred else {
            return nil
        }
        let mediaType = link.mediaType ?? .xhtml

        return Locator(
            href: link.url(),
            mediaType: mediaType,
            title: link.title
        )
    }

    @MainActor
    final class Coordinator: NSObject, EPUBNavigatorDelegate, WKScriptMessageHandler, UIGestureRecognizerDelegate, UIContextMenuInteractionDelegate {
        @Binding private var interactionStatus: String
        @Binding private var noteEditorPresented: Bool
        @Binding private var selectedSentence: String
        @Binding private var redHighlightCount: Int
        private var configuredControllers = Set<ObjectIdentifier>()
        private weak var navigator: EPUBNavigatorViewController?

        init(
            interactionStatus: Binding<String>,
            noteEditorPresented: Binding<Bool>,
            selectedSentence: Binding<String>,
            redHighlightCount: Binding<Int>
        ) {
            _interactionStatus = interactionStatus
            _noteEditorPresented = noteEditorPresented
            _selectedSentence = selectedSentence
            _redHighlightCount = redHighlightCount
        }

        func installSecondaryClickRecognizer(on navigator: EPUBNavigatorViewController) {
            self.navigator = navigator

            let overlay = SecondaryClickCaptureView(frame: navigator.view.bounds)
            overlay.autoresizingMask = [.flexibleWidth, .flexibleHeight]
            overlay.backgroundColor = .clear
            overlay.onSecondaryClick = { [weak self, weak overlay, weak navigator] point in
                guard let self,
                      let overlay,
                      let navigator
                else {
                    return
                }
                self.markSentenceRed(at: overlay.convert(point, to: navigator.view))
            }

            let recognizer = UITapGestureRecognizer(target: self, action: #selector(handleSecondaryClick(_:)))
            recognizer.numberOfTapsRequired = 1
            recognizer.cancelsTouchesInView = true
            recognizer.delegate = self
            overlay.addGestureRecognizer(recognizer)
            overlay.addInteraction(UIContextMenuInteraction(delegate: self))
            navigator.view.addSubview(overlay)
        }

        @objc private func handleSecondaryClick(_ recognizer: UITapGestureRecognizer) {
            guard recognizer.state == .ended,
                  let navigator = navigator,
                  let view = recognizer.view
            else {
                return
            }

            markSentenceRed(at: view.convert(recognizer.location(in: view), to: navigator.view))
        }

        func contextMenuInteraction(
            _ interaction: UIContextMenuInteraction,
            configurationForMenuAtLocation location: CGPoint
        ) -> UIContextMenuConfiguration? {
            guard let view = interaction.view,
                  let navigator = navigator
            else {
                return nil
            }

            markSentenceRed(at: view.convert(location, to: navigator.view))
            return nil
        }

        private func markSentenceRed(at point: CGPoint) {
            guard let navigator = navigator else {
                return
            }
            interactionStatus = "右键命中，正在标红"
            let script = """
            (function () {
              if (window.__sentenceReaderV1ToggleRedAt) {
                return window.__sentenceReaderV1ToggleRedAt(\(point.x), \(point.y));
              }
              return false;
            })();
            """
            Task {
                _ = await navigator.evaluateJavaScript(script)
            }
        }

        func navigator(_ navigator: EPUBNavigatorViewController, setupUserScripts userContentController: WKUserContentController) {
            let id = ObjectIdentifier(userContentController)
            guard !configuredControllers.contains(id) else {
                return
            }
            configuredControllers.insert(id)
            interactionStatus = "正在注入句子交互脚本"

            userContentController.addUserScript(WKUserScript(
                source: Self.sentenceInteractionScript,
                injectionTime: .atDocumentEnd,
                forMainFrameOnly: false
            ))
            userContentController.add(self, name: "sentenceReader")
        }

        func navigator(_ navigator: VisualNavigator, didTapAt point: CGPoint) {
            interactionStatus = "已聚焦当前位置"
        }

        func navigator(_ navigator: Navigator, presentError error: NavigatorError) {
            interactionStatus = "阅读器错误：\(error)"
        }

        nonisolated func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            Task { @MainActor in
                let payload: [String: Any]
                if let dictionary = message.body as? [String: Any] {
                    payload = dictionary
                } else if let dictionary = message.body as? NSDictionary,
                          let bridged = dictionary as? [String: Any]
                {
                    payload = bridged
                } else {
                    return
                }

                guard let type = payload["type"] as? String
                else {
                    return
                }

                let text = (payload["text"] as? String)?
                    .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                if !text.isEmpty {
                    selectedSentence = text
                }

                switch type {
                case "ready":
                    let count = payload["sentenceCount"] as? Int ?? 0
                    interactionStatus = "句子交互已就绪：\(count) 个句子"
                case "focus":
                    interactionStatus = text.isEmpty ? "已聚焦当前句" : "已聚焦：\(text)"
                case "note":
                    noteEditorPresented = true
                    interactionStatus = "正在为当前句添加备注"
                case "red":
                    let isRed = payload["isRed"] as? Bool ?? true
                    let count = payload["redCount"] as? Int ?? redHighlightCount
                    redHighlightCount = count
                    interactionStatus = isRed ? "已整句标红" : "已取消整句标红"
                case "undo":
                    let count = payload["redCount"] as? Int ?? redHighlightCount
                    redHighlightCount = count
                    interactionStatus = text.isEmpty ? "已撤销上一步" : "已撤销：\(text)"
                case "miss":
                    interactionStatus = "没有命中句子"
                default:
                    break
                }
            }
        }

        private static let sentenceInteractionScript = """
        (function () {
          if (window.__sentenceReaderV1Ready) {
            return;
          }
          window.__sentenceReaderV1Ready = true;

          const style = document.createElement('style');
          style.textContent = `
            html, body {
              background: #000 !important;
              color: #f5f5f5 !important;
              font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", "Heiti SC", "Helvetica Neue", Arial, sans-serif !important;
              margin-top: 0 !important;
              margin-bottom: 0 !important;
              padding-top: 0 !important;
              padding-bottom: 0 !important;
            }
            body {
              min-height: 100vh !important;
              line-height: 1.72 !important;
            }
            @media (min-width: 1180px) {
              body {
                max-width: none !important;
                padding-left: 12px !important;
                padding-right: 12px !important;
                column-count: 2 !important;
                column-gap: 24px !important;
                column-fill: auto !important;
              }
              h1, h2, h3, h4, h5, h6, p, blockquote, li {
                break-inside: avoid !important;
              }
            }
            p, li, blockquote, div {
              line-height: 1.72 !important;
            }
            .sr-sentence {
              border-radius: 3px !important;
              cursor: text !important;
              transition: background-color 120ms ease, box-shadow 120ms ease, color 120ms ease !important;
            }
            .sr-sentence.sr-focused {
              background: rgba(64, 156, 255, 0.36) !important;
              box-shadow: 0 0 0 1px rgba(124, 190, 255, 0.52) inset !important;
            }
            .sr-sentence.sr-red {
              background: rgba(255, 59, 48, 0.56) !important;
              color: #fff !important;
              box-shadow: 0 0 0 1px rgba(255, 130, 120, 0.62) inset !important;
            }
            .sr-sentence.sr-red.sr-focused {
              background: rgba(255, 59, 48, 0.62) !important;
              color: #fff !important;
              box-shadow: 0 0 0 1px rgba(255, 170, 160, 0.72) inset !important;
            }
            ::selection {
              background: rgba(255, 214, 10, 0.42) !important;
              color: #fff !important;
            }
            * {
              -webkit-touch-callout: none !important;
            }
          `;
          document.head.appendChild(style);

          function post(payload) {
            try {
              window.webkit.messageHandlers.sentenceReader.postMessage(payload);
            } catch (error) {}
          }

          function sentenceParts(text) {
            const parts = [];
            const regex = /([^。！？!?；;\\n]+[。！？!?；;]+|[^。！？!?；;\\n]+$|\\n+)/g;
            let match;
            while ((match = regex.exec(text)) !== null) {
              parts.push(match[0]);
            }
            return parts.length ? parts : [text];
          }

          function shouldSkip(node) {
            const parent = node.parentElement;
            if (!parent) { return true; }
            if (parent.closest('script, style, noscript, code, pre, textarea, input, .sr-sentence')) {
              return true;
            }
            return !node.nodeValue || !node.nodeValue.trim();
          }

          function wrapTextNode(node, state) {
            if (shouldSkip(node)) {
              return;
            }

            const parts = sentenceParts(node.nodeValue);
            if (parts.length <= 1 && parts[0].trim().length < 8) {
              return;
            }

            const fragment = document.createDocumentFragment();
            for (const part of parts) {
              if (!part.trim()) {
                fragment.appendChild(document.createTextNode(part));
                continue;
              }

              const span = document.createElement('span');
              span.className = 'sr-sentence';
              span.dataset.srIndex = String(state.nextIndex++);
              span.textContent = part;
              fragment.appendChild(span);
            }
            node.parentNode.replaceChild(fragment, node);
          }

          function wrapSentences() {
            const state = { nextIndex: document.querySelectorAll('.sr-sentence').length };
            const roots = document.querySelectorAll('body p, body li, body blockquote, body h1, body h2, body h3, body h4, body h5, body h6');
            for (const root of roots) {
              const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
              const nodes = [];
              while (walker.nextNode()) {
                nodes.push(walker.currentNode);
              }
              for (const node of nodes) {
                wrapTextNode(node, state);
              }
            }
          }

          function sentenceFromTarget(target) {
            if (!target) { return null; }
            target = target.nodeType === Node.TEXT_NODE ? target.parentElement : target;
            return target && target.closest ? target.closest('.sr-sentence') : null;
          }

          function sentenceFromEvent(event) {
            return sentenceFromTarget(event.target) || sentenceFromPoint(event.clientX, event.clientY);
          }

          function sentenceFromPoint(x, y) {
            if (typeof x !== 'number' || typeof y !== 'number') { return null; }
            let sentence = sentenceFromTarget(document.elementFromPoint(x, y));
            if (sentence) { return sentence; }

            const range = document.caretRangeFromPoint ? document.caretRangeFromPoint(x, y) : null;
            sentence = range ? sentenceFromTarget(range.startContainer) : null;
            if (sentence) { return sentence; }

            let best = null;
            let bestDistance = Number.POSITIVE_INFINITY;
            document.querySelectorAll('.sr-sentence').forEach(function (node) {
              const rect = node.getBoundingClientRect();
              if (rect.width <= 0 || rect.height <= 0) { return; }
              if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
                best = node;
                bestDistance = 0;
                return;
              }
              const dx = Math.max(rect.left - x, 0, x - rect.right);
              const dy = Math.max(rect.top - y, 0, y - rect.bottom);
              const distance = Math.sqrt(dx * dx + dy * dy);
              if (distance < bestDistance) {
                bestDistance = distance;
                best = node;
              }
            });
            return bestDistance <= 36 ? best : null;
          }

          function fallbackSentence() {
            const focused = document.querySelector('.sr-sentence.sr-focused');
            if (focused) { return focused; }

            const sentences = Array.from(document.querySelectorAll('.sr-sentence'));
            const visible = sentences.find(function (node) {
              const rect = node.getBoundingClientRect();
              return rect.width > 0 && rect.height > 0 && rect.bottom >= 0 && rect.top <= window.innerHeight;
            });
            return visible || sentences[0] || null;
          }

          function focusSentence(sentence) {
            document.querySelectorAll('.sr-sentence.sr-focused').forEach(function (node) {
              node.classList.remove('sr-focused');
            });
            sentence.classList.add('sr-focused');
            post({
              type: 'focus',
              text: sentence.textContent || '',
              index: sentence.dataset.srIndex || ''
            });
          }

          let lastTap = { time: 0, index: null };
          let tapTimer = null;
          let lastNote = { time: 0, index: null };
          let lastRed = { time: 0, index: null };
          const undoStack = [];

          function openNote(sentence, index, event) {
            const now = Date.now();
            if (lastNote.index === index && (now - lastNote.time) < 520) {
              if (event) {
                event.preventDefault();
                event.stopPropagation();
              }
              return;
            }
            lastNote.time = now;
            lastNote.index = index;
            if (event) {
              event.preventDefault();
              event.stopPropagation();
            }
            focusSentence(sentence);
            post({
              type: 'note',
              text: sentence.textContent || '',
              index: index
            });
          }

          function activatePrimary(event) {
            const sentence = sentenceFromEvent(event);
            if (!sentence) { return; }

            const index = sentence.dataset.srIndex || '';
            const now = Date.now();
            const isDouble = lastTap.index === index && (now - lastTap.time) < 360;
            lastTap = { time: now, index: index };

            if (isDouble) {
              window.clearTimeout(tapTimer);
              openNote(sentence, index, event);
              return;
            }

            window.clearTimeout(tapTimer);
            tapTimer = window.setTimeout(function () {
              focusSentence(sentence);
            }, 120);
          }

          function toggleRedSentence(sentence, event) {
            if (!sentence) {
              post({ type: 'miss' });
              return false;
            }
            const index = sentence.dataset.srIndex || '';
            const now = Date.now();
            if (event) {
              event.preventDefault();
              event.stopPropagation();
            }
            if (lastRed.index === index && (now - lastRed.time) < 320) {
              return true;
            }
            lastRed.time = now;
            lastRed.index = index;
            const wasRed = sentence.classList.contains('sr-red');
            focusSentence(sentence);
            sentence.classList.toggle('sr-red');
            undoStack.push({
              type: 'red',
              index: index,
              wasRed: wasRed,
              text: sentence.textContent || ''
            });
            post({
              type: 'red',
              text: sentence.textContent || '',
              index: index,
              isRed: sentence.classList.contains('sr-red'),
              redCount: document.querySelectorAll('.sr-sentence.sr-red').length
            });
            return true;
          }

          function toggleRed(event) {
            if (event) {
              event.preventDefault();
              event.stopPropagation();
            }
            return toggleRedSentence(sentenceFromEvent(event) || fallbackSentence(), event);
          }

          window.__sentenceReaderV1ToggleRedAt = function (x, y) {
            return toggleRedSentence(sentenceFromPoint(x, y) || fallbackSentence(), null);
          };

          function undoLast() {
            const action = undoStack.pop();
            if (!action) {
              post({
                type: 'undo',
                text: '没有可撤销操作',
                redCount: document.querySelectorAll('.sr-sentence.sr-red').length
              });
              return false;
            }
            if (action.type === 'red') {
              const sentence = document.querySelector('.sr-sentence[data-sr-index="' + action.index + '"]');
              if (sentence) {
                sentence.classList.toggle('sr-red', action.wasRed);
                focusSentence(sentence);
                post({
                  type: 'undo',
                  text: action.text || '',
                  redCount: document.querySelectorAll('.sr-sentence.sr-red').length
                });
              }
            }
            return false;
          }

          window.__sentenceReaderUndo = undoLast;

          document.addEventListener('keydown', function (event) {
            if ((event.metaKey || event.ctrlKey) && !event.shiftKey && event.key && event.key.toLowerCase() === 'z') {
              event.preventDefault();
              event.stopPropagation();
              undoLast();
            }
          }, true);

          document.addEventListener('mouseup', function (event) {
            if (event.button === 0 && !event.ctrlKey) {
              activatePrimary(event);
            }
          }, true);

          document.addEventListener('mousedown', function (event) {
            if (event.button === 0 && !event.ctrlKey) {
              const sentence = sentenceFromEvent(event);
              if (sentence) {
                focusSentence(sentence);
              }
              return;
            }
            if (event.button === 2 || event.ctrlKey) {
              toggleRed(event);
            }
          }, true);

          document.addEventListener('click', function (event) {
            const sentence = sentenceFromEvent(event);
            if (!sentence) { return; }
            focusSentence(sentence);
          }, true);

          document.addEventListener('dblclick', function (event) {
            const sentence = sentenceFromEvent(event);
            if (!sentence) { return; }
            openNote(sentence, sentence.dataset.srIndex || '', event);
          }, true);

          document.addEventListener('contextmenu', function (event) {
              toggleRed(event);
          }, true);
          window.addEventListener('contextmenu', function (event) {
              toggleRed(event);
          }, true);
          document.oncontextmenu = function (event) {
              toggleRed(event);
              return false;
          };

          wrapSentences();

          const observer = new MutationObserver(function () {
            window.clearTimeout(window.__sentenceReaderV1Timer);
            window.__sentenceReaderV1Timer = window.setTimeout(wrapSentences, 80);
          });
          if (document.body) {
            observer.observe(document.body, { childList: true, subtree: true });
          }
          post({
            type: 'ready',
            sentenceCount: document.querySelectorAll('.sr-sentence').length
          });
        })();
        """
    }
}

final class SecondaryClickCaptureView: UIView {
    var onSecondaryClick: ((CGPoint) -> Void)?
    private var lastSecondaryHitAt: TimeInterval = 0

    override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        guard #available(iOS 13.4, *) else {
            return false
        }
        guard event?.buttonMask.contains(.secondary) == true else {
            return false
        }

        let now = ProcessInfo.processInfo.systemUptime
        if now - lastSecondaryHitAt > 0.35 {
            lastSecondaryHitAt = now
            DispatchQueue.main.async { [weak self] in
                self?.onSecondaryClick?(point)
            }
        }
        return true
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard #available(iOS 13.4, *),
              event?.buttonMask.contains(.secondary) == true,
              let touch = touches.first
        else {
            super.touchesEnded(touches, with: event)
            return
        }

        onSecondaryClick?(touch.location(in: self))
    }

    override func pressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
        guard #available(iOS 13.4, *),
              event?.buttonMask.contains(.secondary) == true
        else {
            super.pressesEnded(presses, with: event)
            return
        }

        onSecondaryClick?(CGPoint(x: bounds.midX, y: bounds.midY))
    }
}

struct PublicationLoader {
    func open(filePath: String) async throws -> Publication {
        guard let url = FileURL(path: filePath, isDirectory: false) else {
            throw PublicationLoaderError.invalidFilePath(filePath)
        }

        let httpClient = DefaultHTTPClient()
        let assetRetriever = AssetRetriever(httpClient: httpClient)
        let publicationOpener = PublicationOpener(
            parser: DefaultPublicationParser(
                httpClient: httpClient,
                assetRetriever: assetRetriever,
                pdfFactory: DefaultPDFDocumentFactory()
            )
        )

        let asset = try await assetRetriever.retrieve(url: url).get()
        return try await publicationOpener
            .open(asset: asset, allowUserInteraction: false)
            .get()
    }
}

enum PublicationLoaderError: Error {
    case missingBundledFixture
    case invalidFilePath(String)
}
