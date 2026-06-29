import Foundation
import XCTest
@testable import ReadiumProbe

final class AnnotationPayloadTests: XCTestCase {
    func testAnnotationPayloadRoundTripsThroughJSON() throws {
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
        let data = try JSONEncoder.hermesProbe.encode(payload)
        let decoded = try JSONDecoder.hermesProbe.decode(HermesSyncPayload.self, from: data)

        XCTAssertEqual(decoded, payload)
        XCTAssertEqual(decoded.schemaVersion, "sentence_reader.hermes_sync.v1")
        XCTAssertEqual(decoded.annotation.id, annotation.id)
    }
}

private extension JSONEncoder {
    static var hermesProbe: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }
}

private extension JSONDecoder {
    static var hermesProbe: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}
