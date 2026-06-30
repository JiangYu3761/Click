// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "ReadiumCatalystAdapterProbe",
    platforms: [
        .iOS("15.0"),
    ],
    products: [
        .library(
            name: "ReadiumCatalystAdapterProbe",
            targets: ["ReadiumCatalystAdapterProbe"]
        ),
    ],
    dependencies: [
        .package(path: "/tmp/readium-swift-toolkit-shallow"),
    ],
    targets: [
        .target(
            name: "ReadiumCatalystAdapterProbe",
            dependencies: [
                .product(name: "ReadiumNavigator", package: "readium-swift-toolkit-shallow"),
                .product(name: "ReadiumShared", package: "readium-swift-toolkit-shallow"),
            ]
        ),
    ]
)
