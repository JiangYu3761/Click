import Foundation
import ReadiumShared
import ReadiumStreamer

public struct PublicationOpenSummary: Codable, Equatable {
    public let title: String
    public let authors: [String]
    public let mediaType: String
    public let fileExtension: String
    public let readingOrderCount: Int
    public let tableOfContentsCount: Int
    public let resourceCount: Int
    public let firstReadingOrderHref: String?
}

public struct ReadiumPublicationOpenProbe {
    public init() {}

    public func openSummary(filePath: String) async throws -> PublicationOpenSummary {
        guard let url = FileURL(path: filePath, isDirectory: false) else {
            throw PublicationOpenProbeError.invalidFilePath(filePath)
        }

        let httpClient = DefaultHTTPClient()
        let assetRetriever = AssetRetriever(httpClient: httpClient)
        let publicationOpener = PublicationOpener(
            parser: DefaultPublicationParser(
                httpClient: httpClient,
                assetRetriever: assetRetriever,
                pdfFactory: DefaultPDFDocumentFactory()
            )
        )

        let asset = try await assetRetriever
            .retrieve(url: url)
            .get()

        let publication = try await publicationOpener
            .open(asset: asset, allowUserInteraction: false)
            .get()

        let toc = try await publication.tableOfContents().get()

        return PublicationOpenSummary(
            title: publication.metadata.title ?? "",
            authors: publication.metadata.authors.map(\.name),
            mediaType: asset.format.mediaType?.string ?? "",
            fileExtension: asset.format.fileExtension?.rawValue ?? "",
            readingOrderCount: publication.readingOrder.count,
            tableOfContentsCount: toc.count,
            resourceCount: publication.resources.count,
            firstReadingOrderHref: publication.readingOrder.first?.href
        )
    }
}

public enum PublicationOpenProbeError: Error, Equatable {
    case invalidFilePath(String)
}
