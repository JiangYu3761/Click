// swift-tools-version:6.0

import PackageDescription

let package = Package(
    name: "ReadiumDependencyProbe",
    platforms: [
        .macOS(.v14),
        .iOS(.v15)
    ],
    products: [
        .library(name: "ReadiumDependencyProbe", targets: ["ReadiumDependencyProbe"])
    ],
    dependencies: [
        .package(url: "https://github.com/readium/swift-toolkit.git", branch: "main")
    ],
    targets: [
        .target(
            name: "ReadiumDependencyProbe",
            dependencies: [
                .product(name: "ReadiumShared", package: "swift-toolkit"),
                .product(name: "ReadiumStreamer", package: "swift-toolkit"),
                .product(name: "ReadiumNavigator", package: "swift-toolkit")
            ]
        )
    ]
)

