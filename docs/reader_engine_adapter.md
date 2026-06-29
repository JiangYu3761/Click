# Reader Engine Adapter Boundary

## Purpose

Sentence Reader should not expose Readium-specific types throughout the app.

Readium is still the preferred long-term engine, but its current Swift package is iOS/UIKit-oriented. The app must isolate this risk behind a reader engine adapter so the product model remains stable even if the Mac integration needs extra work.

## Stable App-Level Responsibilities

The app owns:

- Book library records.
- Sentence IDs.
- Annotation database.
- Markdown export.
- Hermes sync payloads.
- UI shell.

The reading engine owns:

- Opening and rendering a publication.
- Reporting current reading location.
- Mapping a user pointer action to a locator/range.
- Applying visual decorations/highlights.
- Navigating to a locator.

## Proposed Adapter Interface

```swift
protocol ReaderEngineAdapter {
    associatedtype ViewHost

    func openBook(at url: URL, initialLocation: String?) async throws -> ViewHost
    func currentLocation() async -> String?
    func sentenceTarget(at point: CGPoint) async throws -> SentenceTarget?
    func applyAnnotations(_ annotations: [ReaderAnnotation]) async
    func goToAnnotation(_ annotation: ReaderAnnotation) async -> Bool
    func observeInput(_ handler: @escaping (ReaderInputEvent) -> Void)
}
```

## Core Types

```swift
struct SentenceTarget: Codable, Equatable {
    let sentenceID: String
    let sourceText: String
    let chapterLocator: String
    let rangeLocatorJSON: String
    let frameInReader: CGRect?
}

struct ReaderAnnotation: Codable, Equatable {
    let id: String
    let sentenceID: String
    let kind: AnnotationKind
    let sourceText: String
    let noteText: String?
    let color: String?
    let rangeLocatorJSON: String
}

enum ReaderInputEvent {
    case focusSentence(SentenceTarget)
    case requestNote(SentenceTarget)
    case toggleRedHighlight(SentenceTarget)
    case activateAnnotation(ReaderAnnotation)
}
```

## Readium Adapter Mapping

Readium concepts map to app concepts like this:

| Sentence Reader | Readium |
| --- | --- |
| `rangeLocatorJSON` | `Locator` encoded as JSON |
| red highlight | `Decoration(style: .highlight(tint: red))` |
| note indicator | `Decoration` with custom style or metadata |
| annotation activation | `observeDecorationInteractions` |
| pointer click | `InputObserving` / `ActivatePointerObserver` |
| current reading position | `Navigator.currentLocation` |

## Current Readium Finding

Positive:

- Readium has `Locator`.
- Readium has `DecorableNavigator`.
- Readium has `Decoration`.
- Readium has pointer input observers and secondary mouse button support.
- Readium highlight persistence is explicitly delegated to the app, which matches our design.

Risk:

- The public Swift package currently declares only `iOS 15.0`.
- The navigator is built with UIKit view controllers.
- The official SwiftUI guide wraps `UIViewController`, not an AppKit `NSView`.
- Full Mac app integration requires full Xcode and likely Mac Catalyst or an adapter wrapper.

## Decision

Continue with Readium as the preferred engine, but do not let app-level data, notes, export, or Hermes sync depend directly on Readium types.

If Readium Mac integration fails after full Xcode testing, replace only this adapter with another engine. The annotation model and UI shell should stay intact.

