import Foundation

public struct ReaderRect: Codable, Equatable, Sendable {
    public let x: Double
    public let y: Double
    public let width: Double
    public let height: Double

    public init(x: Double, y: Double, width: Double, height: Double) {
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    }
}

public struct SentenceTarget: Codable, Equatable, Sendable {
    public let sentenceID: String
    public let sourceText: String
    public let chapterLocator: String
    public let sentenceIndex: Int
    public let rangeLocatorJSON: String
    public let frameInReader: ReaderRect?

    public init(
        sentenceID: String,
        sourceText: String,
        chapterLocator: String,
        sentenceIndex: Int,
        rangeLocatorJSON: String,
        frameInReader: ReaderRect?
    ) {
        self.sentenceID = sentenceID
        self.sourceText = sourceText
        self.chapterLocator = chapterLocator
        self.sentenceIndex = sentenceIndex
        self.rangeLocatorJSON = rangeLocatorJSON
        self.frameInReader = frameInReader
    }
}

public struct ReaderAnnotation: Codable, Equatable, Sendable {
    public let id: String
    public let book: BookReference
    public let sentenceID: String
    public let kind: AnnotationKind
    public let sourceText: String
    public let noteText: String?
    public let color: String?
    public let chapterTitle: String?
    public let chapterLocator: String
    public let rangeLocatorJSON: String
    public let createdAt: Date
    public let updatedAt: Date

    public init(
        id: String,
        book: BookReference,
        sentenceID: String,
        kind: AnnotationKind,
        sourceText: String,
        noteText: String?,
        color: String?,
        chapterTitle: String?,
        chapterLocator: String,
        rangeLocatorJSON: String,
        createdAt: Date,
        updatedAt: Date
    ) {
        self.id = id
        self.book = book
        self.sentenceID = sentenceID
        self.kind = kind
        self.sourceText = sourceText
        self.noteText = noteText
        self.color = color
        self.chapterTitle = chapterTitle
        self.chapterLocator = chapterLocator
        self.rangeLocatorJSON = rangeLocatorJSON
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }

    public init(payload: AnnotationPayload, chapterTitle: String? = nil) {
        let sentenceID = StableID.sentenceID(
            bookHash: payload.book.bookHash,
            chapterLocator: payload.sentence.chapterLocator,
            sentenceIndex: payload.sentence.sentenceIndex,
            sentenceText: payload.sourceText
        )
        self.init(
            id: payload.id,
            book: payload.book,
            sentenceID: sentenceID,
            kind: payload.kind,
            sourceText: payload.sourceText,
            noteText: payload.noteText,
            color: payload.color,
            chapterTitle: chapterTitle,
            chapterLocator: payload.sentence.chapterLocator,
            rangeLocatorJSON: payload.sentence.rangeLocatorJSON,
            createdAt: payload.createdAt,
            updatedAt: payload.updatedAt
        )
    }
}

public enum ReaderInputEvent: Codable, Equatable, Sendable {
    case focusSentence(SentenceTarget)
    case requestNote(SentenceTarget)
    case toggleRedHighlight(SentenceTarget)
    case activateAnnotation(ReaderAnnotation)
}

public protocol ReaderEngineAdapter {
    associatedtype ViewHost

    func openBook(at url: URL, initialLocation: String?) async throws -> ViewHost
    func currentLocation() async -> String?
    func sentenceTarget(at point: ReaderRect) async throws -> SentenceTarget?
    func applyAnnotations(_ annotations: [ReaderAnnotation]) async
    func goToAnnotation(_ annotation: ReaderAnnotation) async -> Bool
    func observeInput(_ handler: @escaping @Sendable (ReaderInputEvent) -> Void)
}

public protocol AnnotationRepository {
    func annotations(for bookHash: String) async throws -> [ReaderAnnotation]
    func annotation(id: String) async throws -> ReaderAnnotation?
    func save(_ annotation: ReaderAnnotation) async throws
    func delete(id: String) async throws
}

