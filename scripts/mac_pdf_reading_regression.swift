// Compiled together with the native reader by run_mac_pdf_reading_regression.py.
private func check(_ pass: @autoclosure () -> Bool, _ message: String) {
    guard pass() else { fatalError(message) }
}

private func pump(_ seconds: TimeInterval = 0.08) {
    RunLoop.main.run(until: Date(timeIntervalSinceNow: seconds))
}

private func createPDF(at file: URL) {
    var page = CGRect(x: 0, y: 0, width: 600, height: 800)
    let context = CGContext(file as CFURL, mediaBox: &page, nil)!
    let style: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 18)]
    for i in 1...5 {
        context.beginPDFPage(nil)
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(cgContext: context, flipped: false)
        ("Read 2:14 and the nearby words." as NSString).draw(at: NSPoint(x: 42, y: 380), withAttributes: style)
        for y in [24, 210, 560, 750] {
            ("The reader on page \(i) at \(y)." as NSString).draw(at: NSPoint(x: 42, y: y), withAttributes: style)
        }
        NSGraphicsContext.restoreGraphicsState()
        context.endPDFPage()
    }
    context.closePDF()
}

private extension MacPDFReaderController {
    func checkSelection(at y: Int) {
        let page = pdfView.currentPage!
        let text = "The reader on page 1 at \(y)."
        let range = (page.string! as NSString).range(of: text)
        check(range.location != NSNotFound, "synthetic line missing")
        let selection = page.selection(for: range)!
        pdfView.setCurrentSelection(selection, animate: false)
        pump()
        view.layoutSubtreeIfNeeded()
        let rect = view.convert(pdfView.convert(selection.bounds(for: page), from: page), from: pdfView)
        check(!actionBar.isHidden && view.bounds.contains(actionBar.frame), "toolbar outside viewport at \(y): \(actionBar.frame)")
        let gap = max(actionBar.frame.minY - rect.maxY, rect.minY - actionBar.frame.maxY)
        check(gap >= -1 && gap <= 8, "toolbar gap \(gap) at \(y)")
        var received = ""
        if y == 210 {
            onNote = { received = $0.sourceText }
            noteButton.performClick(nil)
        } else {
            onToggleHighlight = { received = $0.sourceText }
            highlightButton.performClick(nil)
        }
        check(received == text, "wrong annotation target")
    }
}

private extension LocalReaderSpeech {
    func verifyPlayback(_ text: String, chinese: Bool) {
        var message = ""
        let report: (String) -> Void = { message = $0 }
        speak(text, chinese: chinese, status: report)
        let generating = synthesis
        speak(text, chinese: chinese, status: report)
        check(generating != nil && generating === synthesis, "pending repeat should coalesce")
        let timeout = Date().addingTimeInterval(30)
        while pendingKey != nil && Date() < timeout { pump(0.02) }
        check(player?.isPlaying == true && message.contains("Kokoro"), "did not play natural audio: \(message)")
        speak(text, chinese: chinese, status: report)
        check(player?.isPlaying == true && message.contains("重播"), "replay during audio failed")
        let end = Date().addingTimeInterval((player?.duration ?? 3) + 1)
        while player?.isPlaying == true && Date() < end { pump(0.03) }
        check(player?.isPlaying == false, "playback did not finish")
        speak(text, chinese: chinese, status: report)
        check(player?.isPlaying == true && synthesis == nil, "replay after EOF failed")
    }
}

private extension AppDelegate {
    func checkFixedHeader() {
        buildWindow()
        hideMainLibraryForReading()
        window.contentView?.layoutSubtreeIfNeeded()
        guard let header = readerHeaderView else { fatalError("missing reader toolbar") }
        for content in [webView as NSView, pdfReader.view, comicReader.webView as NSView] {
            check(!header.isHidden && content.frame.maxY <= header.frame.minY + 1, "toolbar overlays reader")
        }
        window.orderOut(nil)
        print("Fixed toolbar reserves a separate row above PDF, EPUB and comic content")
    }

    func checkWordSheet(on host: NSWindow) {
        window = host
        showLookupAlert(bookID: "fixture", word: "reader", sentence: "A reader.", sentenceIndex: "1", payload: nil)
        pump()
        guard let sheet = host.attachedSheet, let root = sheet.contentView else { fatalError("word card missing") }
        func descendants(_ view: NSView) -> [NSView] { [view] + view.subviews.flatMap(descendants) }
        let controls = descendants(root)
        guard let word = controls.compactMap({ $0 as? LookupWordButton }).first else { fatalError("missing replay button") }
        check(controls.compactMap { $0 as? NSTextField }.contains { $0.stringValue.hasPrefix("美 /") }, "missing IPA on word card")
        let timeout = Date().addingTimeInterval(30)
        while !statusLabel.stringValue.contains("Kokoro") && Date() < timeout { pump(0.02) }
        check(statusLabel.stringValue.contains("Kokoro"), "automatic word playback")
        word.performClick(nil)
        check(statusLabel.stringValue.contains("重播"), "actual word button must replay")
        pump(1.8)
        word.performClick(nil)
        check(statusLabel.stringValue.contains("重播"), "same sheet must retain its action target")
        host.endSheet(sheet)
        pump()
        print("Word sheet displayed IPA, autoplayed, and replayed twice through its visible button")
    }
}

private func checkEPUBToolbar() {
    let config = WKWebViewConfiguration()
    config.userContentController.addUserScript(WKUserScript(source: AppDelegate.readerScript, injectionTime: .atDocumentEnd, forMainFrameOnly: true))
    let host = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 760, height: 620),
                        styleMask: [.titled], backing: .buffered, defer: false)
    let web = WKWebView(frame: host.contentView!.bounds, configuration: config)
    host.contentView = web
    host.orderBack(nil)
    let paragraph = String(repeating: "The reader selects words across several lines ", count: 11) + "."
    web.loadHTMLString("<html><body><p>First paragraph.</p><p>\(paragraph)</p></body></html>", baseURL: nil)
    func evaluate(_ code: String) -> Any? {
        var result: Any?
        var done = false
        web.evaluateJavaScript(code) { value, error in
            if let error { fatalError(error.localizedDescription) }
            result = value
            done = true
        }
        let timeout = Date().addingTimeInterval(5)
        while !done && Date() < timeout { pump(0.01) }
        check(done, "WebKit evaluation timed out")
        return result
    }
    let timeout = Date().addingTimeInterval(10)
    while evaluate("!!document.querySelector('.sr-sentence')") as? Bool != true && Date() < timeout { pump() }
    check(evaluate("""
    (() => {
      const sentence = [...document.querySelectorAll('.sr-sentence')].find(e => e.textContent.includes('several lines'));
      if (!sentence) return false;
      const range = document.createRange();
      range.selectNodeContents(sentence);
      const lines = [...range.getClientRects()].filter(r => r.width > 1 && r.height > 1 && r.left >= 0 && r.right <= innerWidth + 1 && r.top >= 0 && r.bottom < innerHeight - 60);
      if (lines.length < 3) return false;
      const start = lines[0], end = lines[lines.length - 1];
      function mouse(name, x, y, buttons) {
        sentence.dispatchEvent(new MouseEvent(name, {bubbles:true, clientX:x, clientY:y, button:0, buttons}));
      }
      mouse('mousedown',start.left + 2,start.top + 2,1);
      getSelection().removeAllRanges(); getSelection().addRange(range);
      mouse('mousemove',end.left + 4,end.top + 2,1);
      mouse('mouseup',end.left + 4,end.top + 2,0);
      window.testEnd = {top:end.top, bottom:end.bottom};
      return true;
    })()
    """) as? Bool == true, "cannot construct a multiline EPUB selection")
    pump(0.5)
    let gap = evaluate("""
    (() => {
      const bar = document.querySelector('#sr-selection-action-bar.sr-visible');
      if (!bar) return -1000;
      const r = bar.getBoundingClientRect();
      return Math.max(testEnd.top-r.bottom, r.top-testEnd.bottom);
    })()
    """) as? Double ?? -1000
    check(gap >= -2 && gap <= 9, "EPUB toolbar gap at drag endpoint: \(gap)")
    print("EPUB WebKit multiline selection toolbar stayed beside the drag endpoint")
}

@main
private enum PDFInteractionRegression {
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)
        let temp = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try! FileManager.default.createDirectory(at: temp, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: temp) }
        AppDelegate().checkFixedHeader()
        let file = temp.appendingPathComponent("sample.pdf")
        createPDF(at: file)
        let reader = MacPDFReaderController()
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 900, height: 700),
                              styleMask: [.titled, .resizable], backing: .buffered, defer: false)
        window.contentView = reader.view
        window.orderBack(nil)
        check(reader.load(url: file, mode: .single, viewportWidth: 900), "PDF load")
        pump()
        let pdf = reader.pdfView
        check(!pdf.enableDataDetectors, "time detector re-enabled by document assignment")
        let page = pdf.currentPage!
        let aroundTime = "2:14 and the nearby words"
        let selected = page.selection(for: (page.string! as NSString).range(of: aroundTime))!
        pdf.setCurrentSelection(selected, animate: false)
        check(pdf.currentSelection?.string == aroundTime, "time blocked text selection")
        pdf.clearSelection()
        reader.restore(locator: ["page_index": 0, "scale_factor": 0.12])
        func assertFit(_ mode: MacPDFFit) {
            let rect = pdf.convert(page.bounds(for: .cropBox), from: page)
            let padding = pdf.pageBreakMargins
            let error = mode == .height
                ? rect.height + padding.top + padding.bottom - pdf.bounds.height
                : rect.width + padding.left + padding.right - pdf.bounds.width
            check(abs(error) < 2, "incorrect fit \(mode): \(error)")
        }
        assertFit(.height)
        reader.setFitMode(.width)
        assertFit(.width)
        window.setContentSize(NSSize(width: 820, height: 640))
        pump()
        assertFit(.width)
        reader.setFitMode(.height)
        assertFit(.height)
        print("Time and adjacent text selected; fit height, fit width, resize and legacy locator passed")
        check(window.makeFirstResponder(reader.pdfView), "PDF focus")
        func arrow(_ code: UInt16, _ flags: NSEvent.ModifierFlags = []) -> Bool {
            let text = code == 124 ? "\u{f703}" : "\u{f702}"
            let key = NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: flags,
                                       timestamp: 0, windowNumber: window.windowNumber, context: nil,
                                       characters: text, charactersIgnoringModifiers: text, isARepeat: false, keyCode: code)!
            let handled = reader.handlePageKey(key)
            pump()
            return handled
        }
        for mode: MacPDFPageMode in [.single, .double, .automatic, .continuous] {
            reader.setPageMode(mode)
            reader.goTo(pageIndex: 0)
            pump()
            check(arrow(123) && reader.currentPageIndex == 0, "left boundary")
            let first = reader.currentPageIndex
            check(arrow(124) && reader.currentPageIndex > first, "right key in \(mode)")
            let second = reader.currentPageIndex
            check(arrow(124) && reader.currentPageIndex > second, "second right key in \(mode): \(second)")
            check(arrow(123) && reader.currentPageIndex == second, "left key in \(mode)")
            check(!arrow(124, .shift), "shift-selection must survive")
        }
        reader.setPageMode(.single)
        reader.goTo(pageIndex: 0)
        pump()
        for y in [24, 210, 560, 750] { reader.checkSelection(at: y) }
        let field = NSTextField(frame: .init(x: 0, y: 0, width: 80, height: 20))
        reader.view.addSubview(field)
        window.makeFirstResponder(field)
        check(!arrow(124), "arrow in editor")
        print("PDF single/spread/continuous keys, editable focus, selection geometry and actions passed")
        checkEPUBToolbar()
        if CommandLine.arguments.count == 2 {
            let runtime = URL(fileURLWithPath: CommandLine.arguments[1])
            let index = runtime.appendingPathComponent("pronunciation.sqlite")
            for word in ["reader", "believing", "sanctification", "read"] {
                check(LookupPronunciation.label(word: word, dictionary: nil, index: index).hasPrefix("美 /"), "IPA: \(word)")
            }
            let speech = LocalReaderSpeech(runtime: runtime)
            speech.verifyPlayback("Reader", chinese: false)
            speech.verifyPlayback("这是中文朗读测试。", chinese: true)
            speech.stop()
            AppDelegate().checkWordSheet(on: window)
            print("Offline IPA, English and Mandarin synthesis, and repeated AVAudioPlayer playback passed")
        }
    }
}
