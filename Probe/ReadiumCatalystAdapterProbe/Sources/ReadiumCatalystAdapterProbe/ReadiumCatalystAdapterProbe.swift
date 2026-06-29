import ReadiumNavigator
import ReadiumShared
import UIKit

@MainActor
public struct ReadiumCatalystAdapterProbe {
    public init() {}

    public func makePlaceholderHost() -> UIViewController {
        UIViewController()
    }

    public func navigatorTypeName() -> String {
        String(describing: EPUBNavigatorViewController.self)
    }

    public func makeNavigatorConfiguration() -> EPUBNavigatorViewController.Configuration {
        EPUBNavigatorViewController.Configuration()
    }

    public func makeSampleSentenceHighlight() -> Decoration {
        let locator = Locator(
            href: AnyURL(string: "chapter-001.xhtml")!,
            mediaType: .xhtml,
            title: "Probe Chapter",
            locations: .init(progression: 0.25),
            text: .init(
                after: "Next sentence.",
                before: "Previous sentence.",
                highlight: "This is the sentence that should be highlighted.",
            )
        )

        return Decoration(
            id: "probe-highlight-001",
            locator: locator,
            style: .highlight(tint: .red),
            userInfo: ["source": "sentence-reader-v1-probe"]
        )
    }

    public func publicContractsAreVisible() -> Bool {
        _ = DecorableNavigator.self
        _ = Decoration.Style.Id.highlight
        _ = EPUBNavigatorViewController.Configuration.self
        return true
    }
}
