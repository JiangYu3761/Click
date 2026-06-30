// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "ReadiumVisualReaderProbe",
    platforms: [
        .iOS("16.0"),
    ],
    products: [
        .executable(
            name: "ReadiumVisualReaderProbe",
            targets: ["ReadiumVisualReaderProbe"]
        ),
    ],
    dependencies: [
        .package(path: "/tmp/readium-swift-toolkit-shallow"),
    ],
    targets: [
        .executableTarget(
            name: "ReadiumVisualReaderProbe",
            dependencies: [
                .product(name: "ReadiumShared", package: "readium-swift-toolkit-shallow"),
                .product(name: "ReadiumStreamer", package: "readium-swift-toolkit-shallow"),
                .product(name: "ReadiumNavigator", package: "readium-swift-toolkit-shallow"),
            ]
        ),
    ]
)
