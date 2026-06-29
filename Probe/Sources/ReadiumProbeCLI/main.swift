import Foundation
import ReadiumProbe

enum SmokeFailure: Error, CustomStringConvertible {
    case failed(String)

    var description: String {
        switch self {
        case .failed(let message):
            return message
        }
    }
}

func expect(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() {
        throw SmokeFailure.failed(message)
    }
}

func runSmoke() async throws {
    let splitter = SentenceBoundaryService()

    let mixed = splitter.split("这是第一句。This is the second sentence. 这是第三句？")
    try expect(
        mixed.map(\.text) == ["这是第一句。", "This is the second sentence.", "这是第三句？"],
        "mixed Chinese/English sentence split failed"
    )

    let decimals = splitter.split("ACOS 从 32.5% 升到 41.2%，先别急着关广告。判断要看 CTR、CVR 和 CPC。")
    try expect(
        decimals.map(\.text) == ["ACOS 从 32.5% 升到 41.2%，先别急着关广告。", "判断要看 CTR、CVR 和 CPC。"],
        "decimal sentence split failed"
    )

    let book = BookReference(title: "Positioning", author: "Al Ries", bookHash: "bookhash")
    let sentenceText = "The basic approach of positioning is not to create something new and different."
    let sentenceID = StableID.sentenceID(
        bookHash: book.bookHash,
        chapterLocator: "chapter-1",
        sentenceIndex: 7,
        sentenceText: sentenceText
    )
    let locator = SentenceLocator(
        chapterLocator: "chapter-1",
        sentenceIndex: 7,
        sentenceTextHash: StableID.fnv1a64Hex(sentenceText),
        rangeLocatorJSON: #"{"href":"chapter1.xhtml","locations":{"cfi":"/4/2/8"}}"#
    )
    let now = Date(timeIntervalSince1970: 1_800_000_000)
    let annotation = AnnotationPayload(
        id: StableID.annotationID(sentenceID: sentenceID, kind: .note),
        book: book,
        sentence: locator,
        kind: .note,
        sourceText: sentenceText,
        noteText: "This is a mental model about occupying an existing category in the reader's mind.",
        color: nil,
        createdAt: now,
        updatedAt: now
    )
    let payload = HermesSyncPayload(annotation: annotation, cognitiveHint: "positioning")
    let encoder = JSONEncoder()
    encoder.dateEncodingStrategy = .iso8601
    encoder.outputFormatting = [.sortedKeys]
    let data = try encoder.encode(payload)

    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    let decoded = try decoder.decode(HermesSyncPayload.self, from: data)
    try expect(decoded == payload, "Hermes sync payload JSON round trip failed")

    let noteAnnotation = ReaderAnnotation(payload: annotation, chapterTitle: "Chapter 1")
    let redAnnotation = ReaderAnnotation(
        id: StableID.annotationID(sentenceID: sentenceID, kind: .redHighlight),
        book: book,
        sentenceID: sentenceID,
        kind: .redHighlight,
        sourceText: "A market leader should not be attacked with the same words.",
        noteText: nil,
        color: "red",
        chapterTitle: "Chapter 1",
        chapterLocator: "chapter-1",
        rangeLocatorJSON: #"{"href":"chapter1.xhtml","locations":{"cfi":"/4/2/10"}}"#,
        createdAt: now.addingTimeInterval(60),
        updatedAt: now.addingTimeInterval(60)
    )

    let repository = InMemoryAnnotationRepository()
    try await repository.save(noteAnnotation)
    try await repository.save(redAnnotation)
    let stored = try await repository.annotations(for: book.bookHash)
    try expect(stored.count == 2, "annotation repository did not return saved annotations")
    try expect(stored.map(\.kind) == [.note, .redHighlight], "annotation repository ordering changed")

    let markdown = MarkdownExporter().export(book: book, annotations: stored)
    try expect(markdown.contains("# Positioning"), "markdown export missing title")
    try expect(markdown.contains("> The basic approach of positioning"), "markdown export missing source sentence")
    try expect(markdown.contains("Red highlight"), "markdown export missing red highlight")
    try expect(markdown.contains("Hermes hint:"), "markdown export missing Hermes hint")

    print("readium-probe smoke PASS")
    print("sentences=\(mixed.count + decimals.count)")
    print("payload_schema=\(decoded.schemaVersion)")
    print("annotations=\(stored.count)")
    print("markdown_chars=\(markdown.count)")
}

do {
    try await runSmoke()
} catch {
    fputs("readium-probe smoke FAIL: \(error)\n", stderr)
    exit(1)
}
