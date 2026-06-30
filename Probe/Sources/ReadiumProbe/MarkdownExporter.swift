import Foundation

public struct MarkdownExportOptions: Codable, Equatable, Sendable {
    public let includeMetadata: Bool
    public let includeHermesHint: Bool

    public init(includeMetadata: Bool = true, includeHermesHint: Bool = true) {
        self.includeMetadata = includeMetadata
        self.includeHermesHint = includeHermesHint
    }
}

public struct MarkdownExporter: Sendable {
    public init() {}

    public func export(book: BookReference, annotations: [ReaderAnnotation], options: MarkdownExportOptions = MarkdownExportOptions()) -> String {
        var lines: [String] = []
        lines.append("# \(escapeHeading(book.title))")
        if let author = book.author, !author.isEmpty {
            lines.append("")
            lines.append("Author: \(author)")
        }
        lines.append("")

        let grouped = Dictionary(grouping: annotations) { annotation in
            annotation.chapterTitle ?? annotation.chapterLocator
        }

        for chapter in grouped.keys.sorted() {
            lines.append("## \(escapeHeading(chapter))")
            lines.append("")

            let chapterAnnotations = (grouped[chapter] ?? []).sorted { left, right in
                if left.chapterLocator != right.chapterLocator {
                    return left.chapterLocator < right.chapterLocator
                }
                if left.createdAt != right.createdAt {
                    return left.createdAt < right.createdAt
                }
                return left.id < right.id
            }

            for annotation in chapterAnnotations {
                append(annotation: annotation, to: &lines, options: options)
            }
        }

        return lines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines) + "\n"
    }

    private func append(annotation: ReaderAnnotation, to lines: inout [String], options: MarkdownExportOptions) {
        lines.append("> \(annotation.sourceText.normalizedForMarkdownQuote)")
        lines.append("")

        switch annotation.kind {
        case .note:
            lines.append("Note:")
            lines.append((annotation.noteText ?? "").trimmingCharacters(in: .whitespacesAndNewlines).emptyFallback("(empty note)"))
        case .redHighlight:
            lines.append("Red highlight")
        }

        if options.includeHermesHint {
            lines.append("")
            lines.append("Hermes hint:")
            lines.append("- Preserve the source sentence before drawing conclusions.")
            lines.append("- Extract reusable mental model only when the note contains a real judgment.")
        }

        if options.includeMetadata {
            lines.append("")
            lines.append("Metadata:")
            lines.append("- id: \(annotation.id)")
            lines.append("- kind: \(annotation.kind.rawValue)")
            lines.append("- chapter_locator: \(annotation.chapterLocator)")
            lines.append("- locator: \(annotation.rangeLocatorJSON)")
        }

        lines.append("")
    }

    private func escapeHeading(_ value: String) -> String {
        value.replacingOccurrences(of: "\n", with: " ").trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

private extension String {
    var normalizedForMarkdownQuote: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
            .components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
            .joined(separator: " ")
    }

    func emptyFallback(_ fallback: String) -> String {
        isEmpty ? fallback : self
    }
}

