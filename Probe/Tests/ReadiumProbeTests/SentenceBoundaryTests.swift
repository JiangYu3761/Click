import XCTest
@testable import ReadiumProbe

final class SentenceBoundaryTests: XCTestCase {
    func testSplitsChineseAndEnglishSentences() {
        let text = "这是第一句。This is the second sentence. 这是第三句？"
        let sentences = SentenceBoundaryService().split(text)

        XCTAssertEqual(sentences.map(\.text), [
            "这是第一句。",
            "This is the second sentence.",
            "这是第三句？"
        ])
    }

    func testDoesNotSplitDecimalNumbers() {
        let text = "ACOS 从 32.5% 升到 41.2%，先别急着关广告。判断要看 CTR、CVR 和 CPC。"
        let sentences = SentenceBoundaryService().split(text)

        XCTAssertEqual(sentences.map(\.text), [
            "ACOS 从 32.5% 升到 41.2%，先别急着关广告。",
            "判断要看 CTR、CVR 和 CPC。"
        ])
    }

    func testKeepsTrailingChineseQuoteWithSentence() {
        let text = "他说：“定位不是口号。”然后停顿。"
        let sentences = SentenceBoundaryService().split(text)

        XCTAssertEqual(sentences.map(\.text), [
            "他说：“定位不是口号。”",
            "然后停顿。"
        ])
    }
}
