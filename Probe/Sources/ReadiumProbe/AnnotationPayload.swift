import Foundation

public enum AnnotationKind: String, Codable, Equatable, Sendable {
    case note
    case redHighlight = "red_highlight"
}

public struct BookReference: Codable, Equatable, Sendable {
    public let title: String
    public let author: String?
    public let bookHash: String

    public init(title: String, author: String?, bookHash: String) {
        self.title = title
        self.author = author
        self.bookHash = bookHash
    }
}

public struct SentenceLocator: Codable, Equatable, Sendable {
    public let chapterLocator: String
    public let sentenceIndex: Int
    public let sentenceTextHash: String
    public let rangeLocatorJSON: String

    public init(chapterLocator: String, sentenceIndex: Int, sentenceTextHash: String, rangeLocatorJSON: String) {
        self.chapterLocator = chapterLocator
        self.sentenceIndex = sentenceIndex
        self.sentenceTextHash = sentenceTextHash
        self.rangeLocatorJSON = rangeLocatorJSON
    }
}

public struct AnnotationPayload: Codable, Equatable, Sendable {
    public let id: String
    public let book: BookReference
    public let sentence: SentenceLocator
    public let kind: AnnotationKind
    public let sourceText: String
    public let noteText: String?
    public let color: String?
    public let createdAt: Date
    public let updatedAt: Date

    public init(
        id: String,
        book: BookReference,
        sentence: SentenceLocator,
        kind: AnnotationKind,
        sourceText: String,
        noteText: String?,
        color: String?,
        createdAt: Date,
        updatedAt: Date
    ) {
        self.id = id
        self.book = book
        self.sentence = sentence
        self.kind = kind
        self.sourceText = sourceText
        self.noteText = noteText
        self.color = color
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

public struct HermesSyncPayload: Codable, Equatable, Sendable {
    public let schemaVersion: String
    public let source: String
    public let annotation: AnnotationPayload
    public let cognitiveHint: String?

    public init(annotation: AnnotationPayload, cognitiveHint: String? = nil) {
        self.schemaVersion = "sentence_reader.hermes_sync.v1"
        self.source = "sentence-reader-mac"
        self.annotation = annotation
        self.cognitiveHint = cognitiveHint
    }
}

public enum StableID {
    public static func sentenceID(bookHash: String, chapterLocator: String, sentenceIndex: Int, sentenceText: String) -> String {
        let textHash = fnv1a64Hex(sentenceText.normalizedForIdentity)
        return [bookHash, chapterLocator, String(sentenceIndex), textHash].joined(separator: ":")
    }

    public static func annotationID(sentenceID: String, kind: AnnotationKind) -> String {
        fnv1a64Hex("\(sentenceID):\(kind.rawValue)")
    }

    public static func fnv1a64Hex(_ value: String) -> String {
        var hash: UInt64 = 0xcbf29ce484222325
        for byte in value.utf8 {
            hash ^= UInt64(byte)
            hash = hash &* 0x100000001b3
        }
        return String(format: "%016llx", hash)
    }
}

private extension String {
    var normalizedForIdentity: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: #"\s+"#, with: " ", options: .regularExpression)
    }
}

