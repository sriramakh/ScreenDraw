import Cocoa

protocol ToolbarPanelDelegate: AnyObject {
    func toolbarDidSelectTool(_ tool: DrawingTool)
    func toolbarDidSelectColor(_ color: NSColor)
    func toolbarDidSelectLineWidth(_ width: CGFloat)
    func toolbarDidRequestUndo()
    func toolbarDidRequestRedo()
    func toolbarDidRequestClear()
    func toolbarDidRequestToggleDrawing()
    func toolbarDidRequestScreenshot()
    func toolbarDidRequestWhiteboard()
    func toolbarDidRequestBlackboard()
    func toolbarDidRequestCursorHighlight()
    func toolbarDidRequestCursorShape()
    func toolbarDidRequestSpotlight()
    func toolbarDidRequestZoom()
    func toolbarDidRequestLaser()
    func toolbarDidRequestClickAnim()
    func toolbarDidRequestRecord()
    func toolbarDidRequestMinimize()
    func toolbarDidRequestQuit()
}

class ToolbarPanel: NSPanel {

    weak var toolbarDelegate: ToolbarPanelDelegate?

    private var toolButtons: [NSButton] = []
    private var colorButtons: [NSButton] = []
    private var sizeSlider: NSSlider!
    private var drawingToggleButton: NSButton!
    private var whiteboardButton: NSButton!
    private var blackboardButton: NSButton!
    private var cursorHighlightButton: NSButton!
    private var cursorShapeButton: NSButton!
    private var spotlightButton: NSButton!
    private var zoomButton: NSButton!
    private var laserButton: NSButton!
    private var clickAnimButton: NSButton!
    private var recordButton: NSButton!

    private var selectedToolIndex = 0
    private var selectedColorIndex = 0

    private let tools = DrawingTool.allDrawingTools

    private let panelWidth: CGFloat = 52
    private let buttonSize: CGFloat = 36
    private let spacing: CGFloat = 4

    init() {
        let totalHeight: CGFloat = 1120
        let screenFrame = NSScreen.main?.visibleFrame ?? .zero

        let panelRect = NSRect(
            x: screenFrame.maxX - panelWidth - 16,
            y: screenFrame.midY - totalHeight / 2,
            width: panelWidth,
            height: totalHeight
        )

        super.init(
            contentRect: panelRect,
            styleMask: [.nonactivatingPanel, .titled, .closable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )

        self.isFloatingPanel = true
        self.level = NSWindow.Level(Int(CGWindowLevelForKey(.screenSaverWindow)) + 1)
        self.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        self.isOpaque = false
        self.backgroundColor = .clear
        self.sharingType = .none // Hidden from screen sharing
        self.titleVisibility = .hidden
        self.titlebarAppearsTransparent = true
        self.isMovableByWindowBackground = true
        self.hasShadow = true
        self.becomesKeyOnlyIfNeeded = true

        setupUI()
    }

    private func setupUI() {
        let containerView = NSVisualEffectView(frame: self.contentView!.bounds)
        containerView.autoresizingMask = [.width, .height]
        containerView.material = .hudWindow
        containerView.blendingMode = .behindWindow
        containerView.state = .active
        containerView.wantsLayer = true
        containerView.layer?.cornerRadius = 14
        containerView.layer?.masksToBounds = true
        self.contentView = containerView

        let stackView = NSStackView()
        stackView.orientation = .vertical
        stackView.spacing = spacing
        stackView.alignment = .centerX
        stackView.translatesAutoresizingMaskIntoConstraints = false
        containerView.addSubview(stackView)

        NSLayoutConstraint.activate([
            stackView.topAnchor.constraint(equalTo: containerView.topAnchor, constant: 12),
            stackView.bottomAnchor.constraint(lessThanOrEqualTo: containerView.bottomAnchor, constant: -12),
            stackView.centerXAnchor.constraint(equalTo: containerView.centerXAnchor),
            stackView.widthAnchor.constraint(equalToConstant: buttonSize)
        ])

        // Drawing toggle button
        drawingToggleButton = makeSymbolButton(symbolName: "pencil.circle.fill", action: #selector(toggleDrawing), tooltip: "Toggle Drawing (D)")
        drawingToggleButton.contentTintColor = .systemGreen
        stackView.addArrangedSubview(drawingToggleButton)
        addConstraintsForButton(drawingToggleButton)

        stackView.addArrangedSubview(makeSeparator())

        // Tool buttons
        let toolLabel = makeLabel("Tools")
        stackView.addArrangedSubview(toolLabel)

        for (index, tool) in tools.enumerated() {
            let button = makeSymbolButton(
                symbolName: tool.symbolName,
                action: #selector(toolSelected(_:)),
                tooltip: "\(tool.rawValue) (\(index + 1))"
            )
            button.tag = index
            toolButtons.append(button)
            stackView.addArrangedSubview(button)
            addConstraintsForButton(button)
        }

        updateToolSelection()

        stackView.addArrangedSubview(makeSeparator())

        // Screenshot button
        let screenshotBtn = makeSymbolButton(symbolName: "camera.viewfinder", action: #selector(screenshotAction), tooltip: "Screenshot (S)")
        screenshotBtn.contentTintColor = .systemBlue
        stackView.addArrangedSubview(screenshotBtn)
        addConstraintsForButton(screenshotBtn)

        stackView.addArrangedSubview(makeSeparator())

        // Color buttons
        let colorLabel = makeLabel("Color")
        stackView.addArrangedSubview(colorLabel)

        for (index, (color, name)) in colorPalette.enumerated() {
            let button = makeColorButton(color: color, action: #selector(colorSelected(_:)), tooltip: name)
            button.tag = index
            colorButtons.append(button)
            stackView.addArrangedSubview(button)
            addConstraintsForButton(button)
        }

        updateColorSelection()

        stackView.addArrangedSubview(makeSeparator())

        // Size slider
        let sizeLabel = makeLabel("Size")
        stackView.addArrangedSubview(sizeLabel)

        sizeSlider = NSSlider(value: 3.0, minValue: 1.0, maxValue: 20.0, target: self, action: #selector(sizeChanged(_:)))
        sizeSlider.controlSize = .small
        sizeSlider.translatesAutoresizingMaskIntoConstraints = false
        sizeSlider.isVertical = true
        stackView.addArrangedSubview(sizeSlider)
        NSLayoutConstraint.activate([
            sizeSlider.heightAnchor.constraint(equalToConstant: 60),
            sizeSlider.widthAnchor.constraint(equalToConstant: buttonSize)
        ])

        stackView.addArrangedSubview(makeSeparator())

        // Board buttons
        let boardLabel = makeLabel("Board")
        stackView.addArrangedSubview(boardLabel)

        whiteboardButton = makeSymbolButton(symbolName: "rectangle.fill", action: #selector(whiteboardAction), tooltip: "Whiteboard (W)")
        whiteboardButton.contentTintColor = .lightGray
        stackView.addArrangedSubview(whiteboardButton)
        addConstraintsForButton(whiteboardButton)

        blackboardButton = makeSymbolButton(symbolName: "rectangle.fill", action: #selector(blackboardAction), tooltip: "Blackboard (B)")
        blackboardButton.contentTintColor = .darkGray
        stackView.addArrangedSubview(blackboardButton)
        addConstraintsForButton(blackboardButton)

        cursorHighlightButton = makeSymbolButton(symbolName: "target", action: #selector(cursorHighlightAction), tooltip: "Cursor Highlight (H)")
        cursorHighlightButton.contentTintColor = .systemYellow
        stackView.addArrangedSubview(cursorHighlightButton)
        addConstraintsForButton(cursorHighlightButton)

        cursorShapeButton = makeSymbolButton(symbolName: "circle.dashed", action: #selector(cursorShapeAction), tooltip: "Cursor Shape (Shift+H)")
        cursorShapeButton.contentTintColor = .systemYellow
        stackView.addArrangedSubview(cursorShapeButton)
        addConstraintsForButton(cursorShapeButton)

        spotlightButton = makeSymbolButton(symbolName: "light.max", action: #selector(spotlightAction), tooltip: "Spotlight (F)")
        spotlightButton.contentTintColor = .systemOrange
        stackView.addArrangedSubview(spotlightButton)
        addConstraintsForButton(spotlightButton)

        zoomButton = makeSymbolButton(symbolName: "magnifyingglass", action: #selector(zoomAction), tooltip: "Zoom Lens (Z)")
        zoomButton.contentTintColor = .systemIndigo
        stackView.addArrangedSubview(zoomButton)
        addConstraintsForButton(zoomButton)

        laserButton = makeSymbolButton(symbolName: "smallcircle.filled.circle", action: #selector(laserAction), tooltip: "Laser Pointer (L)")
        laserButton.contentTintColor = .systemRed
        stackView.addArrangedSubview(laserButton)
        addConstraintsForButton(laserButton)

        clickAnimButton = makeSymbolButton(symbolName: "circle.circle", action: #selector(clickAnimAction), tooltip: "Click Animations (K)")
        clickAnimButton.contentTintColor = .systemPink
        stackView.addArrangedSubview(clickAnimButton)
        addConstraintsForButton(clickAnimButton)

        stackView.addArrangedSubview(makeSeparator())

        // Action buttons
        let undoBtn = makeSymbolButton(symbolName: "arrow.uturn.backward", action: #selector(undoAction), tooltip: "Undo (Cmd+Z)")
        stackView.addArrangedSubview(undoBtn)
        addConstraintsForButton(undoBtn)

        let redoBtn = makeSymbolButton(symbolName: "arrow.uturn.forward", action: #selector(redoAction), tooltip: "Redo (Cmd+Shift+Z)")
        stackView.addArrangedSubview(redoBtn)
        addConstraintsForButton(redoBtn)

        let clearBtn = makeSymbolButton(symbolName: "trash", action: #selector(clearAction), tooltip: "Clear All (C)")
        clearBtn.contentTintColor = .systemRed
        stackView.addArrangedSubview(clearBtn)
        addConstraintsForButton(clearBtn)

        stackView.addArrangedSubview(makeSeparator())

        recordButton = makeSymbolButton(symbolName: "record.circle", action: #selector(recordAction), tooltip: "Record Screen (R)")
        recordButton.contentTintColor = .systemRed
        stackView.addArrangedSubview(recordButton)
        addConstraintsForButton(recordButton)

        stackView.addArrangedSubview(makeSeparator())

        let minimizeBtn = makeSymbolButton(symbolName: "minus.circle.fill", action: #selector(minimizeAction), tooltip: "Minimize (M)")
        minimizeBtn.contentTintColor = .systemOrange
        stackView.addArrangedSubview(minimizeBtn)
        addConstraintsForButton(minimizeBtn)

        let quitBtn = makeSymbolButton(symbolName: "xmark.circle.fill", action: #selector(quitAction), tooltip: "Quit (Esc / Cmd+Q)")
        quitBtn.contentTintColor = .systemGray
        stackView.addArrangedSubview(quitBtn)
        addConstraintsForButton(quitBtn)
    }

    // MARK: - UI Helpers

    private func makeSymbolButton(symbolName: String, action: Selector, tooltip: String) -> NSButton {
        let button: NSButton
        if let image = NSImage(systemSymbolName: symbolName, accessibilityDescription: tooltip) {
            let config = NSImage.SymbolConfiguration(pointSize: 16, weight: .medium)
            let configuredImage = image.withSymbolConfiguration(config) ?? image
            button = NSButton(image: configuredImage, target: self, action: action)
        } else {
            button = NSButton(title: String(symbolName.prefix(2)), target: self, action: action)
        }
        button.isBordered = false
        button.bezelStyle = .regularSquare
        button.toolTip = tooltip
        button.translatesAutoresizingMaskIntoConstraints = false
        button.wantsLayer = true
        button.layer?.cornerRadius = 8
        return button
    }

    private func makeColorButton(color: NSColor, action: Selector, tooltip: String) -> NSButton {
        let button = NSButton(frame: .zero)
        button.isBordered = false
        button.title = ""
        button.target = self
        button.action = action
        button.toolTip = tooltip
        button.translatesAutoresizingMaskIntoConstraints = false
        button.wantsLayer = true
        button.layer?.cornerRadius = buttonSize / 2 - 4
        button.layer?.backgroundColor = color.cgColor
        if color == .white || color == .systemYellow {
            button.layer?.borderColor = NSColor.gray.withAlphaComponent(0.5).cgColor
            button.layer?.borderWidth = 1
        }
        return button
    }

    private func makeLabel(_ text: String) -> NSTextField {
        let label = NSTextField(labelWithString: text)
        label.font = .systemFont(ofSize: 8, weight: .semibold)
        label.textColor = .secondaryLabelColor
        label.alignment = .center
        return label
    }

    private func makeSeparator() -> NSBox {
        let sep = NSBox()
        sep.boxType = .separator
        sep.translatesAutoresizingMaskIntoConstraints = false
        return sep
    }

    private func addConstraintsForButton(_ button: NSButton) {
        NSLayoutConstraint.activate([
            button.widthAnchor.constraint(equalToConstant: buttonSize),
            button.heightAnchor.constraint(equalToConstant: buttonSize - 4)
        ])
    }

    // MARK: - Selection Updates

    private func updateToolSelection() {
        for (index, button) in toolButtons.enumerated() {
            button.layer?.backgroundColor = (index == selectedToolIndex)
                ? NSColor.controlAccentColor.withAlphaComponent(0.3).cgColor
                : NSColor.clear.cgColor
        }
    }

    func selectTool(at index: Int) {
        selectedToolIndex = index
        updateToolSelection()
    }

    private func updateColorSelection() {
        for (index, button) in colorButtons.enumerated() {
            if index == selectedColorIndex {
                button.layer?.borderColor = NSColor.controlAccentColor.cgColor
                button.layer?.borderWidth = 2.5
            } else {
                let (color, _) = colorPalette[index]
                if color == .white || color == .systemYellow {
                    button.layer?.borderColor = NSColor.gray.withAlphaComponent(0.5).cgColor
                    button.layer?.borderWidth = 1
                } else {
                    button.layer?.borderWidth = 0
                }
            }
        }
    }

    func updateDrawingToggle(isEnabled: Bool) {
        drawingToggleButton.contentTintColor = isEnabled ? .systemGreen : .systemGray
        drawingToggleButton.toolTip = isEnabled ? "Drawing ON (D to toggle)" : "Drawing OFF (D to toggle)"
    }

    func updateBoardButtons(mode: BoardMode) {
        whiteboardButton.layer?.backgroundColor = (mode == .whiteboard)
            ? NSColor.controlAccentColor.withAlphaComponent(0.3).cgColor
            : NSColor.clear.cgColor
        blackboardButton.layer?.backgroundColor = (mode == .blackboard)
            ? NSColor.controlAccentColor.withAlphaComponent(0.3).cgColor
            : NSColor.clear.cgColor
    }

    func updateCursorHighlightButton(isEnabled: Bool) {
        cursorHighlightButton.layer?.backgroundColor = isEnabled
            ? NSColor.systemYellow.withAlphaComponent(0.3).cgColor
            : NSColor.clear.cgColor
    }

    func updateRecordButton(isRecording: Bool) {
        recordButton.layer?.backgroundColor = isRecording
            ? NSColor.systemRed.withAlphaComponent(0.2).cgColor
            : NSColor.clear.cgColor
        recordButton.toolTip = isRecording ? "Stop Recording (R)" : "Record Screen (R)"
    }

    func updateSpotlightButton(isEnabled: Bool) {
        spotlightButton.layer?.backgroundColor = isEnabled
            ? NSColor.systemOrange.withAlphaComponent(0.3).cgColor
            : NSColor.clear.cgColor
    }

    func updateZoomButton(isEnabled: Bool) {
        zoomButton.layer?.backgroundColor = isEnabled
            ? NSColor.systemIndigo.withAlphaComponent(0.3).cgColor
            : NSColor.clear.cgColor
    }

    func updateLaserButton(isEnabled: Bool) {
        laserButton.layer?.backgroundColor = isEnabled
            ? NSColor.systemRed.withAlphaComponent(0.2).cgColor
            : NSColor.clear.cgColor
    }

    func updateClickAnimButton(isEnabled: Bool) {
        clickAnimButton.layer?.backgroundColor = isEnabled
            ? NSColor.systemPink.withAlphaComponent(0.3).cgColor
            : NSColor.clear.cgColor
    }

    func updateCursorShapeButton(shapeName: String) {
        cursorShapeButton.toolTip = "Cursor Shape: \(shapeName) (Shift+H)"
    }

    // MARK: - Actions

    @objc private func toolSelected(_ sender: NSButton) {
        selectedToolIndex = sender.tag
        updateToolSelection()
        toolbarDelegate?.toolbarDidSelectTool(tools[sender.tag])
    }

    @objc private func colorSelected(_ sender: NSButton) {
        selectedColorIndex = sender.tag
        updateColorSelection()
        toolbarDelegate?.toolbarDidSelectColor(colorPalette[sender.tag].0)
    }

    @objc private func sizeChanged(_ sender: NSSlider) {
        toolbarDelegate?.toolbarDidSelectLineWidth(CGFloat(sender.doubleValue))
    }

    @objc private func screenshotAction() { toolbarDelegate?.toolbarDidRequestScreenshot() }
    @objc private func whiteboardAction() { toolbarDelegate?.toolbarDidRequestWhiteboard() }
    @objc private func blackboardAction() { toolbarDelegate?.toolbarDidRequestBlackboard() }
    @objc private func cursorHighlightAction() { toolbarDelegate?.toolbarDidRequestCursorHighlight() }
    @objc private func cursorShapeAction() { toolbarDelegate?.toolbarDidRequestCursorShape() }
    @objc private func spotlightAction() { toolbarDelegate?.toolbarDidRequestSpotlight() }
    @objc private func zoomAction() { toolbarDelegate?.toolbarDidRequestZoom() }
    @objc private func laserAction() { toolbarDelegate?.toolbarDidRequestLaser() }
    @objc private func clickAnimAction() { toolbarDelegate?.toolbarDidRequestClickAnim() }
    @objc private func undoAction() { toolbarDelegate?.toolbarDidRequestUndo() }
    @objc private func redoAction() { toolbarDelegate?.toolbarDidRequestRedo() }
    @objc private func clearAction() { toolbarDelegate?.toolbarDidRequestClear() }
    @objc private func toggleDrawing() { toolbarDelegate?.toolbarDidRequestToggleDrawing() }
    @objc private func recordAction() { toolbarDelegate?.toolbarDidRequestRecord() }
    @objc private func minimizeAction() { toolbarDelegate?.toolbarDidRequestMinimize() }
    @objc private func quitAction() { toolbarDelegate?.toolbarDidRequestQuit() }
}
