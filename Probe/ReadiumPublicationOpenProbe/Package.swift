// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "ReadiumPublicationOpenProbe",
    platforms: [
        .iOS("15.0"),
    ],
    products: [
        .library(
            name: "ReadiumPublicationOpenProbe",
            targets: ["ReadiumPublicationOpenProbe"]
        ),
    ],
    dependencies: [
        .package(path: "/tmp/readium-swift-toolkit-shallow"),
    ],
    targets: [
        .target(
            name: "ReadiumPublicationOpenProbe",
            dependencies: [
                .product(name: "ReadiumShared", package: "readium-swift-toolkit-shallow"),
                .product(name: "ReadiumStreamer", package: "readium-swift-toolkit-shallow"),
            ]
        ),
        .testTarget(
            name: "ReadiumPublicationOpenProbeTests",
            dependencies: ["ReadiumPublicationOpenProbe"]
        ),
    ]
)
