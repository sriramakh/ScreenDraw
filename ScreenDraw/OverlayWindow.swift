import Cocoa

class OverlayWindow: NSWindow {

    init(screen: NSScreen) {
        super.init(
            contentRect: screen.frame,
            styleMask: .borderless,
            backing: .buffered,
            defer: false
        )

        self.setFrame(screen.frame, display: true)
        self.isOpaque = false
        self.backgroundColor = .clear
        self.level = .screenSaver
        self.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        self.ignoresMouseEvents = false
        self.hasShadow = false
        self.isReleasedWhenClosed = false
        self.acceptsMouseMovedEvents = true
        self.sharingType = .none // Hidden from screen sharing (Zoom, Teams, Meet)
    }

    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }
}
