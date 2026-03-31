// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "ScreenDraw",
    platforms: [
        .macOS(.v13)
    ],
    targets: [
        .executableTarget(
            name: "ScreenDraw",
            path: "ScreenDraw",
            linkerSettings: [
                .linkedFramework("Cocoa"),
                .linkedFramework("AppKit"),
            ]
        )
    ]
)
