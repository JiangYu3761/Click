# Readium Probe Acceptance

## Purpose

The Readium probe decides whether Readium can be the long-term engine for the Sentence Reader Mac app.

This probe is not a UI polish task. It is a risk test for the core product promise:

`tap/click position -> sentence range -> whole sentence annotation -> persisted decoration`

## Must Prove

1. The project can resolve Readium Swift Toolkit as a dependency. Done.
2. A local EPUB fixture can be parsed or opened through the Readium stack. Done: `ReadiumPublicationOpenProbe`.
3. The probe can represent a sentence-level target using a stable locator/range structure.
4. A sentence splitter can handle Chinese and English punctuation. Done in local core.
5. Annotation data can round-trip through JSON without losing range identity. Done in local core.
6. The eventual Mac app can keep Readium behind an adapter boundary. Partly done: `ReadiumCatalystAdapterProbe` compiles.

## Nice To Prove

- Readium navigator can expose click or selection events with enough locator data.
- Readium decoration/highlight APIs can restore saved sentence annotations.
- PDF support can be kept separate from EPUB support.

## Failure Conditions

Readium should be reconsidered if:

- It cannot be resolved or built in the local macOS toolchain.
- Its APIs cannot expose enough location/range information for sentence-level annotation.
- The Mac integration requires heavy private workarounds.

Failure does not kill the product. It only means the reading engine adapter needs a different implementation.

## Probe Outputs

- `Probe/Package.swift`
- `Probe/ReadiumCatalystAdapterProbe/Package.swift`
- `Probe/ReadiumCatalystAdapterProbe/Sources/ReadiumCatalystAdapterProbe/ReadiumCatalystAdapterProbe.swift`
- sentence boundary service
- annotation payload model
- unit tests for sentence splitting and annotation round-trip
- dependency resolution notes
- `reports/readium_xcode_build_probe.json`
- `reports/readium_catalyst_adapter_probe.json`
- `reports/readium_publication_open_probe.json`
- `reports/readium_publication_open_summary.json`
- recommendation: proceed, adjust, or replace engine

## Current Gate

Readium has passed dependency resolution, Mac Catalyst compile, and real EPUB opening gates. The remaining V1 gate is navigator interaction behavior:

`render real EPUB -> user points at sentence -> adapter produces stable Locator/Text -> Decoration restores after restart`
