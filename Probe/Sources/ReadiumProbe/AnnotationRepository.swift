import Foundation

public actor InMemoryAnnotationRepository: AnnotationRepository {
    private var storage: [String: ReaderAnnotation] = [:]

    public init(annotations: [ReaderAnnotation] = []) {
        for annotation in annotations {
            storage[annotation.id] = annotation
        }
    }

    public func annotations(for bookHash: String) async throws -> [ReaderAnnotation] {
        storage.values
            .filter { $0.book.bookHash == bookHash }
            .sorted { left, right in
                if left.chapterLocator != right.chapterLocator {
                    return left.chapterLocator < right.chapterLocator
                }
                if left.createdAt != right.createdAt {
                    return left.createdAt < right.createdAt
                }
                return left.id < right.id
            }
    }

    public func annotation(id: String) async throws -> ReaderAnnotation? {
        storage[id]
    }

    public func save(_ annotation: ReaderAnnotation) async throws {
        storage[annotation.id] = annotation
    }

    public func delete(id: String) async throws {
        storage[id] = nil
    }
}

