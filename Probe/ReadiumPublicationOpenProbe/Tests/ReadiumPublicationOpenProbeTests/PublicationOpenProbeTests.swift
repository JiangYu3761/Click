import Foundation
import XCTest
@testable import ReadiumPublicationOpenProbe

final class PublicationOpenProbeTests: XCTestCase {
    func testOpensEPUBFixtureWithReadiumStreamer() async throws {
        let fixturePath = [
            ProcessInfo.processInfo.environment["SENTENCE_READER_EPUB_FIXTURE"],
            "/tmp/sentence-reader-fixtures/good-strategy-bad-strategy.epub",
            "/Users/jiangyu/Desktop/好战略坏战略(理查德·鲁梅尔特[RumeltRichard]).epub"
        ]
        .compactMap { $0 }
        .first { FileManager.default.fileExists(atPath: $0) }
        ?? ""

        XCTAssertTrue(
            FileManager.default.fileExists(atPath: fixturePath),
            "Missing EPUB fixture. Checked SENTENCE_READER_EPUB_FIXTURE, /tmp runtime copy, and the legacy Desktop fixture."
        )

        let summary = try await ReadiumPublicationOpenProbe()
            .openSummary(filePath: fixturePath)

        let summaryPath = ProcessInfo.processInfo.environment["SENTENCE_READER_PUBLICATION_OPEN_SUMMARY"]
            ?? "/tmp/sentence-reader-readium-publication-open-summary.json"
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(summary)
        try data.write(to: URL(fileURLWithPath: summaryPath))

        XCTAssertFalse(summary.title.isEmpty)
        XCTAssertEqual(summary.mediaType, "application/epub+zip")
        XCTAssertGreaterThan(summary.readingOrderCount, 0)
        XCTAssertGreaterThan(summary.tableOfContentsCount, 0)
        XCTAssertNotNil(summary.firstReadingOrderHref)
    }
}
