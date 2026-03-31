import Cocoa
import AVFoundation

class AppDelegate: NSObject, NSApplicationDelegate {

    var overlayWindow: OverlayWindow!
    var drawingView: DrawingView!
    var toolbarPanel: ToolbarPanel!
    var statusItem: NSStatusItem!
    var isDrawingActive = true

    // Text input
    private var textInputField: NSTextField?
    private var textInputPoint: CGPoint?
    private var textJustCommitted = false

    // Screen recording
    private var isRecording = false
    private var captureSession: AVCaptureSession?
    private var movieOutput: AVCaptureMovieFileOutput?
    private var recordingPath: String?

    // MARK: - App Lifecycle

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)

        setupStatusBarItem()
        setupOverlayWindow()
        setupToolbar()
        setupKeyboardShortcuts()

        activateDrawing()
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if isRecording { stopRecording() }
        return .terminateNow
    }

    // MARK: - Status Bar

    private func setupStatusBarItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)

        if let button = statusItem.button {
            if let image = NSImage(systemSymbolName: "pencil.tip.crop.circle", accessibilityDescription: "ScreenDraw") {
                let config = NSImage.SymbolConfiguration(pointSize: 16, weight: .medium)
                button.image = image.withSymbolConfiguration(config) ?? image
            } else {
                button.title = "SD"
            }
        }

        let menu = NSMenu()
        menu.addItem(withTitle: "Toggle Drawing (D)", action: #selector(toggleDrawingMode), keyEquivalent: "d")
        menu.addItem(withTitle: "Show/Hide (M)", action: #selector(restoreFromMenu), keyEquivalent: "m")
        menu.addItem(withTitle: "Record Screen (R)", action: #selector(recordFromMenu), keyEquivalent: "r")
        menu.addItem(NSMenuItem.separator())
        menu.addItem(withTitle: "Undo", action: #selector(undoAction), keyEquivalent: "z")
        menu.addItem(withTitle: "Redo", action: #selector(redoAction), keyEquivalent: "Z")
        menu.addItem(withTitle: "Clear All", action: #selector(clearAction), keyEquivalent: "")
        menu.addItem(NSMenuItem.separator())

        let toolNames = DrawingTool.allDrawingTools
        for (i, tool) in toolNames.enumerated() {
            let item = NSMenuItem(title: tool.rawValue, action: #selector(selectToolFromMenu(_:)), keyEquivalent: "\(i + 1)")
            item.tag = i
            menu.addItem(item)
        }

        menu.addItem(NSMenuItem.separator())
        menu.addItem(withTitle: "Screenshot (S)", action: #selector(screenshotFromMenu), keyEquivalent: "s")
        menu.addItem(withTitle: "Whiteboard (W)", action: #selector(whiteboardFromMenu), keyEquivalent: "w")
        menu.addItem(withTitle: "Blackboard (B)", action: #selector(blackboardFromMenu), keyEquivalent: "b")
        menu.addItem(NSMenuItem.separator())
        menu.addItem(withTitle: "Quit ScreenDraw", action: #selector(quitApp), keyEquivalent: "q")

        for item in menu.items {
            item.target = self
        }

        statusItem.menu = menu
    }

    // MARK: - Overlay Window

    private func setupOverlayWindow() {
        guard let screen = NSScreen.main else { return }

        overlayWindow = OverlayWindow(screen: screen)

        drawingView = DrawingView(frame: screen.frame)
        drawingView.autoresizingMask = [.width, .height]
        drawingView.onTextRequested = { [weak self] point in
            self?.handleTextRequest(at: point)
        }
        drawingView.onKeyEvent = { [weak self] event in
            return self?.processKeyEvent(event) ?? false
        }
        overlayWindow.contentView = drawingView

        overlayWindow.makeKeyAndOrderFront(nil)
        overlayWindow.makeFirstResponder(drawingView)
    }

    // MARK: - Toolbar

    private func setupToolbar() {
        toolbarPanel = ToolbarPanel()
        toolbarPanel.toolbarDelegate = self
        toolbarPanel.orderFront(nil)
    }

    // MARK: - Keyboard Shortcuts

    private func setupKeyboardShortcuts() {
        NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            guard let self = self else { return event }
            if self.processKeyEvent(event) { return nil }
            return event
        }

        NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
            guard let self = self else { return }
            // Fallback for Esc and Cmd+Q when window doesn't have focus
            let mods = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
            if event.keyCode == 53 || (mods == .command && event.keyCode == 12) {
                self.quitApp()
            }
        }
    }

    private func processKeyEvent(_ event: NSEvent) -> Bool {
        // Guard: if text was just committed, swallow stale events
        if textJustCommitted {
            textJustCommitted = false
            return true
        }

        // If text input is active, handle Enter/Escape
        if textInputField != nil {
            if event.keyCode == 36 { // Return
                commitTextInput()
                return true
            } else if event.keyCode == 53 { // Escape
                cancelTextInput()
                return true
            }
            return false // Let text field handle other keys
        }

        let modifiers = event.modifierFlags.intersection(.deviceIndependentFlagsMask)

        // Cmd+Z = Undo
        if modifiers == .command && event.keyCode == 6 {
            drawingView.undo()
            return true
        }
        // Cmd+Shift+Z = Redo
        if modifiers == [.command, .shift] && event.keyCode == 6 {
            drawingView.redo()
            return true
        }
        // Cmd+Q = Quit
        if modifiers == .command && event.keyCode == 12 {
            quitApp()
            return true
        }
        // Escape = Quit
        if event.keyCode == 53 {
            quitApp()
            return true
        }

        guard modifiers.isEmpty || modifiers == .shift else { return false }

        guard let chars = event.charactersIgnoringModifiers?.lowercased() else { return false }

        switch chars {
        case "d":
            toggleDrawingMode()
            return true
        case "1": setTool(.pen, index: 0); return true
        case "2": setTool(.highlighter, index: 1); return true
        case "3": setTool(.line, index: 2); return true
        case "4": setTool(.arrow, index: 3); return true
        case "5": setTool(.rectangle, index: 4); return true
        case "6": setTool(.circle, index: 5); return true
        case "7": setTool(.text, index: 6); return true
        case "8": setTool(.eraser, index: 7); return true
        case "9": setTool(.fadingInk, index: 8); return true
        case "s":
            activateScreenshotMode()
            return true
        case "w":
            toggleWhiteboard()
            return true
        case "b":
            toggleBlackboard()
            return true
        case "h":
            if modifiers == .shift {
                cycleCursorShape()
            } else {
                toggleCursorHighlight()
            }
            return true
        case "f":
            toggleSpotlight()
            return true
        case "z":
            toggleZoom()
            return true
        case "l":
            toggleLaserPointer()
            return true
        case "k":
            toggleClickAnimations()
            return true
        case "r":
            toggleRecording()
            return true
        case "m":
            minimizeApp()
            return true
        case "c":
            drawingView.clearAll()
            return true
        case "[", "-":
            let w = max(1, drawingView.engine.currentLineWidth - 1)
            drawingView.setLineWidth(w)
            return true
        case "]", "=", "+":
            let w = min(30, drawingView.engine.currentLineWidth + 1)
            drawingView.setLineWidth(w)
            return true
        default:
            return false
        }
    }

    private func setTool(_ tool: DrawingTool, index: Int) {
        drawingView.engine.currentTool = tool
        toolbarPanel.selectTool(at: index)
    }

    // MARK: - Drawing State

    private func activateDrawing() {
        isDrawingActive = true
        drawingView.isDrawingEnabled = true
        overlayWindow.ignoresMouseEvents = false
        overlayWindow.makeKeyAndOrderFront(nil)
        toolbarPanel.updateDrawingToggle(isEnabled: true)
        NSCursor.crosshair.set()
    }

    private func deactivateDrawing() {
        isDrawingActive = false
        drawingView.isDrawingEnabled = false
        overlayWindow.ignoresMouseEvents = true
        toolbarPanel.updateDrawingToggle(isEnabled: false)
        NSCursor.arrow.set()
    }

    // MARK: - Minimize / Restore

    private func minimizeApp() {
        deactivateDrawing()
        overlayWindow.orderOut(nil)
        toolbarPanel.orderOut(nil)
    }

    private func restoreApp() {
        overlayWindow.makeKeyAndOrderFront(nil)
        toolbarPanel.orderFront(nil)
        activateDrawing()
    }

    // MARK: - Cursor Highlight

    private func toggleCursorHighlight() {
        let enabled = !drawingView.cursorHighlightEnabled
        drawingView.cursorHighlightEnabled = enabled
        if !enabled {
            drawingView.needsDisplay = true
        }
        toolbarPanel.updateCursorHighlightButton(isEnabled: enabled)
    }

    // MARK: - Cursor Shape

    private func cycleCursorShape() {
        let shapes = CursorHighlightShape.allCases
        let currentIdx = shapes.firstIndex(of: drawingView.cursorHighlightShape) ?? 0
        let nextIdx = (currentIdx + 1) % shapes.count
        drawingView.cursorHighlightShape = shapes[nextIdx]
        if drawingView.cursorHighlightEnabled {
            drawingView.needsDisplay = true
        }
        toolbarPanel.updateCursorShapeButton(shapeName: shapes[nextIdx].rawValue)
    }

    // MARK: - Spotlight

    private func toggleSpotlight() {
        let enabled = !drawingView.spotlightEnabled
        drawingView.spotlightEnabled = enabled
        if !enabled {
            drawingView.needsDisplay = true
        }
        toolbarPanel.updateSpotlightButton(isEnabled: enabled)
    }

    // MARK: - Zoom

    private func toggleZoom() {
        let enabled = !drawingView.zoomEnabled
        drawingView.zoomEnabled = enabled
        if !enabled {
            drawingView.needsDisplay = true
        }
        toolbarPanel.updateZoomButton(isEnabled: enabled)
    }

    // MARK: - Laser Pointer

    private func toggleLaserPointer() {
        let enabled = !drawingView.laserPointerEnabled
        drawingView.laserPointerEnabled = enabled
        if !enabled {
            drawingView.needsDisplay = true
        }
        toolbarPanel.updateLaserButton(isEnabled: enabled)
    }

    // MARK: - Click Animations

    private func toggleClickAnimations() {
        let enabled = !drawingView.clickAnimationsEnabled
        drawingView.clickAnimationsEnabled = enabled
        toolbarPanel.updateClickAnimButton(isEnabled: enabled)
    }

    // MARK: - Whiteboard / Blackboard

    private func toggleWhiteboard() {
        let engine = drawingView.engine
        engine.boardMode = (engine.boardMode == .whiteboard) ? .none : .whiteboard
        drawingView.needsDisplay = true
        toolbarPanel.updateBoardButtons(mode: engine.boardMode)
    }

    private func toggleBlackboard() {
        let engine = drawingView.engine
        engine.boardMode = (engine.boardMode == .blackboard) ? .none : .blackboard
        drawingView.needsDisplay = true
        toolbarPanel.updateBoardButtons(mode: engine.boardMode)
    }

    // MARK: - Screenshot

    private func activateScreenshotMode() {
        // For now, use the system screenshot shortcut
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
        task.arguments = ["-i", "-c"] // interactive, to clipboard
        // Temporarily hide windows for clean capture
        overlayWindow.orderOut(nil)
        toolbarPanel.orderOut(nil)

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { [weak self] in
            try? task.run()
            task.waitUntilExit()

            DispatchQueue.main.async {
                self?.overlayWindow.makeKeyAndOrderFront(nil)
                self?.toolbarPanel.orderFront(nil)
            }
        }
    }

    // MARK: - Screen Recording

    private func toggleRecording() {
        if isRecording {
            stopRecording()
        } else {
            startRecording()
        }
    }

    private func startRecording() {
        guard !isRecording else { return }

        let session = AVCaptureSession()
        session.sessionPreset = .high

        let displayID = CGMainDisplayID()
        guard let screenInput = AVCaptureScreenInput(displayID: displayID) else {
            print("ScreenDraw: Failed to create screen capture input")
            return
        }
        screenInput.minFrameDuration = CMTimeMake(value: 1, timescale: 30)
        screenInput.capturesMouseClicks = true
        screenInput.capturesCursor = true

        guard session.canAddInput(screenInput) else {
            print("ScreenDraw: Cannot add screen input to session")
            return
        }
        session.addInput(screenInput)

        let output = AVCaptureMovieFileOutput()
        guard session.canAddOutput(output) else {
            print("ScreenDraw: Cannot add movie output to session")
            return
        }
        session.addOutput(output)

        let desktop = NSHomeDirectory() + "/Desktop"
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd_HH-mm-ss"
        let timestamp = formatter.string(from: Date())
        let filepath = "\(desktop)/ScreenDraw_Recording_\(timestamp).mov"

        captureSession = session
        movieOutput = output
        recordingPath = filepath

        session.startRunning()
        output.startRecording(to: URL(fileURLWithPath: filepath), recordingDelegate: self)

        isRecording = true
        toolbarPanel.updateRecordButton(isRecording: true)
        print("ScreenDraw: Recording started -> \(filepath)")
    }

    private func stopRecording() {
        guard isRecording else { return }
        movieOutput?.stopRecording()
    }

    // MARK: - Text Input

    private func handleTextRequest(at point: CGPoint) {
        if textInputField != nil {
            cancelTextInput()
        }

        textInputPoint = point
        let fieldWidth: CGFloat = 300
        let fieldHeight: CGFloat = 30
        let fontSize = drawingView.engine.currentFontSize

        let field = NSTextField(frame: NSRect(x: point.x, y: point.y - fieldHeight / 2, width: fieldWidth, height: fieldHeight))
        field.font = NSFont.systemFont(ofSize: fontSize)
        field.textColor = drawingView.engine.currentColor
        field.drawsBackground = false
        field.backgroundColor = .clear
        field.isBordered = true
        field.isEditable = true
        field.isSelectable = true
        field.stringValue = ""
        field.placeholderString = "Type text, press Enter"
        field.target = self
        field.action = #selector(textFieldAction(_:))

        drawingView.addSubview(field)
        overlayWindow.makeFirstResponder(field)
        textInputField = field
    }

    @objc private func textFieldAction(_ sender: NSTextField) {
        commitTextInput()
    }

    private func commitTextInput() {
        guard let field = textInputField else { return }
        textJustCommitted = true
        let text = field.stringValue
        if !text.isEmpty, let point = textInputPoint {
            drawingView.engine.addTextStroke(text, at: point)
        }
        field.removeFromSuperview()
        textInputField = nil
        textInputPoint = nil
        drawingView.needsDisplay = true
        overlayWindow.makeFirstResponder(drawingView)
    }

    private func cancelTextInput() {
        textInputField?.removeFromSuperview()
        textInputField = nil
        textInputPoint = nil
        overlayWindow.makeFirstResponder(drawingView)
    }

    // MARK: - Menu Actions

    @objc func toggleDrawingMode() {
        if isDrawingActive { deactivateDrawing() }
        else { activateDrawing() }
    }

    @objc func undoAction() { drawingView.undo() }
    @objc func redoAction() { drawingView.redo() }
    @objc func clearAction() { drawingView.clearAll() }

    @objc func selectToolFromMenu(_ sender: NSMenuItem) {
        let tools = DrawingTool.allDrawingTools
        guard sender.tag < tools.count else { return }
        setTool(tools[sender.tag], index: sender.tag)
    }

    @objc func screenshotFromMenu() { activateScreenshotMode() }
    @objc func whiteboardFromMenu() { toggleWhiteboard() }
    @objc func blackboardFromMenu() { toggleBlackboard() }
    @objc func recordFromMenu() { toggleRecording() }

    @objc func restoreFromMenu() {
        if overlayWindow.isVisible { minimizeApp() }
        else { restoreApp() }
    }

    @objc func quitApp() {
        NSApplication.shared.terminate(nil)
    }
}

// MARK: - ToolbarPanelDelegate

extension AppDelegate: ToolbarPanelDelegate {
    func toolbarDidSelectTool(_ tool: DrawingTool) {
        drawingView.setTool(tool)
    }

    func toolbarDidSelectColor(_ color: NSColor) {
        drawingView.setColor(color)
    }

    func toolbarDidSelectLineWidth(_ width: CGFloat) {
        drawingView.setLineWidth(width)
    }

    func toolbarDidRequestUndo() { drawingView.undo() }
    func toolbarDidRequestRedo() { drawingView.redo() }
    func toolbarDidRequestClear() { drawingView.clearAll() }
    func toolbarDidRequestToggleDrawing() { toggleDrawingMode() }
    func toolbarDidRequestScreenshot() { activateScreenshotMode() }
    func toolbarDidRequestWhiteboard() { toggleWhiteboard() }
    func toolbarDidRequestBlackboard() { toggleBlackboard() }
    func toolbarDidRequestCursorHighlight() { toggleCursorHighlight() }
    func toolbarDidRequestCursorShape() { cycleCursorShape() }
    func toolbarDidRequestSpotlight() { toggleSpotlight() }
    func toolbarDidRequestZoom() { toggleZoom() }
    func toolbarDidRequestLaser() { toggleLaserPointer() }
    func toolbarDidRequestClickAnim() { toggleClickAnimations() }
    func toolbarDidRequestRecord() { toggleRecording() }
    func toolbarDidRequestMinimize() { minimizeApp() }
    func toolbarDidRequestQuit() { quitApp() }
}

// MARK: - AVCaptureFileOutputRecordingDelegate

extension AppDelegate: AVCaptureFileOutputRecordingDelegate {
    func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo outputFileURL: URL,
                    from connections: [AVCaptureConnection], error: Error?) {
        captureSession?.stopRunning()
        captureSession = nil
        movieOutput = nil
        isRecording = false

        DispatchQueue.main.async { [weak self] in
            self?.toolbarPanel.updateRecordButton(isRecording: false)
        }

        if let error = error {
            print("ScreenDraw: Recording error: \(error.localizedDescription)")
        } else {
            print("ScreenDraw: Recording saved to \(outputFileURL.path)")
        }
        recordingPath = nil
    }
}
