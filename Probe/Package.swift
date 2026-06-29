// swift-tools-version:6.0

import PackageDescription

let package = Package(
    name: "ReadiumProbe",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(name: "ReadiumProbe", targets: ["ReadiumProbe"]),
        .executable(name: "readium-probe", targets: ["ReadiumProbeCLI"]),
        .executable(name: "sentence-reader-app-probe", targets: ["SentenceReaderAppProbe"])
    ],
    targets: [
        .target(name: "ReadiumProbe"),
        .executableTarget(
            name: "ReadiumProbeCLI",
            dependencies: ["ReadiumProbe"]
        ),
        .executableTarget(
            name: "SentenceReaderAppProbe",
            dependencies: ["ReadiumProbe"]
        ),
        .testTarget(
            name: "ReadiumProbeTests",
            dependencies: ["ReadiumProbe"]
        )
    ]
)
