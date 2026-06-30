import Foundation

public struct SentenceCandidate: Codable, Equatable, Sendable {
    public let index: Int
    public let text: String
    public let startOffset: Int
    public let endOffset: Int

    public init(index: Int, text: String, startOffset: Int, endOffset: Int) {
        self.index = index
        self.text = text
        self.startOffset = startOffset
        self.endOffset = endOffset
    }
}

public struct SentenceBoundaryService: Sendable {
    private let strongTerminators = Set<Character>(["。", "！", "？", "!", "?", "；", ";"])
    private let trailingClosers = Set<Character>(["”", "’", "\"", "'", ")", "）", "]", "】", "》"])

    public init() {}

    public func split(_ text: String) -> [SentenceCandidate] {
        var sentences: [SentenceCandidate] = []
        var sentenceStart = text.startIndex
        var offsetStart = 0
        var currentOffset = 0
        var nextIndex = 0

        var index = text.startIndex
        while index < text.endIndex {
            let character = text[index]
            currentOffset += 1

            if shouldEndSentence(on: character, in: text, at: index) {
                var end = text.index(after: index)
                var endOffset = currentOffset
                while end < text.endIndex, trailingClosers.contains(text[end]) {
                    end = text.index(after: end)
                    endOffset += 1
                }
                appendSentence(
                    from: sentenceStart,
                    to: end,
                    startOffset: offsetStart,
                    endOffset: endOffset,
                    index: &nextIndex,
                    text: text,
                    output: &sentences
                )
                sentenceStart = end
                offsetStart = endOffset
                index = end
                continue
            }

            index = text.index(after: index)
        }

        appendSentence(
            from: sentenceStart,
            to: text.endIndex,
            startOffset: offsetStart,
            endOffset: text.count,
            index: &nextIndex,
            text: text,
            output: &sentences
        )

        return sentences
    }

    private func shouldEndSentence(on character: Character, in text: String, at index: String.Index) -> Bool {
        if strongTerminators.contains(character) {
            return true
        }

        guard character == "." else {
            return false
        }

        let previous = previousNonSpace(in: text, before: index)
        let next = nextNonSpace(in: text, after: index)

        if previous?.isNumber == true, next?.isNumber == true {
            return false
        }

        if let previous, previous.isUppercaseLetter, next?.isLowercaseLetter == true {
            return false
        }

        if let next {
            return next.isUppercaseLetter || next.isCJK || next.isQuoteOrCloser
        }

        return true
    }

    private func appendSentence(
        from start: String.Index,
        to end: String.Index,
        startOffset: Int,
        endOffset: Int,
        index: inout Int,
        text: String,
        output: inout [SentenceCandidate]
    ) {
        let raw = String(text[start..<end])
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return
        }
        output.append(
            SentenceCandidate(
                index: index,
                text: trimmed,
                startOffset: startOffset,
                endOffset: endOffset
            )
        )
        index += 1
    }

    private func previousNonSpace(in text: String, before index: String.Index) -> Character? {
        var cursor = index
        while cursor > text.startIndex {
            cursor = text.index(before: cursor)
            let character = text[cursor]
            if !character.isWhitespace {
                return character
            }
        }
        return nil
    }

    private func nextNonSpace(in text: String, after index: String.Index) -> Character? {
        var cursor = text.index(after: index)
        while cursor < text.endIndex {
            let character = text[cursor]
            if !character.isWhitespace {
                return character
            }
            cursor = text.index(after: cursor)
        }
        return nil
    }
}

private extension Character {
    var isNumber: Bool {
        unicodeScalars.allSatisfy { CharacterSet.decimalDigits.contains($0) }
    }

    var isUppercaseLetter: Bool {
        guard let scalar = unicodeScalars.first, unicodeScalars.count == 1 else {
            return false
        }
        return CharacterSet.uppercaseLetters.contains(scalar)
    }

    var isLowercaseLetter: Bool {
        guard let scalar = unicodeScalars.first, unicodeScalars.count == 1 else {
            return false
        }
        return CharacterSet.lowercaseLetters.contains(scalar)
    }

    var isQuoteOrCloser: Bool {
        Set<Character>(["”", "’", "\"", "'", ")", "）", "]", "】", "》"]).contains(self)
    }

    var isCJK: Bool {
        unicodeScalars.contains { scalar in
            (0x4E00...0x9FFF).contains(Int(scalar.value))
                || (0x3400...0x4DBF).contains(Int(scalar.value))
                || (0xF900...0xFAFF).contains(Int(scalar.value))
        }
    }
}
