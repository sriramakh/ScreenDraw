import Cocoa
import QuartzCore

class DrawingView: NSView {
    let engine = DrawingEngine()
    var isDrawingEnabled = true
    var onStrokeChanged: (() -> Void)?
    var onTextRequested: ((CGPoint) -> Void)?
    var onScreenshotTaken: ((CGPoint, CGPoint) -> Void)?
    var onKeyEvent: ((NSEvent) -> Bool)?

    var cursorHighlightEnabled = false
    var cursorHighlightRadius: CGFloat = 30.0
    var cursorHighlightShape: CursorHighlightShape = .circle
    private var cursorPoint: CGPoint?
    private var fadeTimer: Timer?

    // Trackpad draw mode: 1 finger = draw, 2 fingers = move cursor only
    var trackpadDrawMode = false
    private var trackpadTouchCount = 0
    private var isTrackpadDrawing = false

    // Spotlight
    var spotlightEnabled = false
    var spotlightRadius: CGFloat = spotlightRadiusDefault

    // Zoom
    var zoomEnabled = false
    var zoomFactor: CGFloat = zoomFactorDefault

    // Laser pointer
    var laserPointerEnabled = false

    // Click animations
    var clickAnimationsEnabled = false
    var clickAnims: [ClickAnimation] = []
    private var animTimer: Timer?

    override var acceptsFirstResponder: Bool { true }
    override var isFlipped: Bool { false }

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        setupView()
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setupView()
    }

    private func setupView() {
        wantsLayer = true
        layer?.backgroundColor = NSColor.clear.cgColor
        // Enable trackpad (indirect) touch events for trackpad draw mode
        allowedTouchTypes = [.indirect]
    }

    // MARK: - Drawing

    override func draw(_ dirtyRect: NSRect) {
        guard let context = NSGraphicsContext.current?.cgContext else { return }

        // Board background
        switch engine.boardMode {
        case .whiteboard:
            NSColor.white.setFill()
            dirtyRect.fill()
        case .blackboard:
            NSColor.black.setFill()
            dirtyRect.fill()
        case .none:
            context.clear(dirtyRect)
        }

        engine.draw(in: context, dirtyRect: dirtyRect)

        // Spotlight — dim everything except circle around cursor
        if spotlightEnabled, let pt = cursorPoint {
            let sr = spotlightRadius
            NSColor.black.withAlphaComponent(spotlightDimAlpha).setFill()
            dirtyRect.fill()
            context.setBlendMode(.clear)
            let spotRect = CGRect(x: pt.x - sr, y: pt.y - sr, width: sr * 2, height: sr * 2)
            context.fillEllipse(in: spotRect)
            context.setBlendMode(.normal)
        }

        // Zoom lens — magnified view around cursor
        if zoomEnabled, let pt = cursorPoint {
            let zr = zoomLensRadius
            let zf = zoomFactor
            context.saveGState()
            let lensRect = CGRect(x: pt.x - zr, y: pt.y - zr, width: zr * 2, height: zr * 2)
            let lensPath = CGPath(ellipseIn: lensRect, transform: nil)
            context.addPath(lensPath)
            context.clip()
            context.translateBy(x: pt.x, y: pt.y)
            context.scaleBy(x: zf, y: zf)
            context.translateBy(x: -pt.x, y: -pt.y)
            engine.draw(in: context, dirtyRect: dirtyRect)
            context.restoreGState()
            // Lens border
            NSColor.white.withAlphaComponent(0.8).setStroke()
            let borderPath = NSBezierPath(ovalIn: lensRect)
            borderPath.lineWidth = 2.5
            borderPath.stroke()
        }

        // Cursor highlight with shapes
        if cursorHighlightEnabled, let pt = cursorPoint {
            let r = cursorHighlightRadius
            let highlightRect = CGRect(x: pt.x - r, y: pt.y - r, width: r * 2, height: r * 2)

            switch cursorHighlightShape {
            case .squircle:
                let cornerRadius = r * 0.35
                engine.currentColor.withAlphaComponent(0.25).setFill()
                let sqPath = NSBezierPath(roundedRect: highlightRect, xRadius: cornerRadius, yRadius: cornerRadius)
                sqPath.fill()
                engine.currentColor.withAlphaComponent(0.5).setStroke()
                sqPath.lineWidth = 1.5
                sqPath.stroke()

            case .ring:
                let ringPath = NSBezierPath(ovalIn: highlightRect)
                engine.currentColor.withAlphaComponent(0.6).setStroke()
                ringPath.lineWidth = 3.0
                ringPath.stroke()

            case .circle:
                engine.currentColor.withAlphaComponent(0.25).setFill()
                let path = NSBezierPath(ovalIn: highlightRect)
                path.fill()
                engine.currentColor.withAlphaComponent(0.5).setStroke()
                path.lineWidth = 1.5
                path.stroke()
            }
        }

        // Laser pointer — small red dot with glow
        if laserPointerEnabled, let pt = cursorPoint {
            let lr = laserPointerRadius
            // Glow
            NSColor.red.withAlphaComponent(0.3).setFill()
            let glowRect = CGRect(x: pt.x - lr * 2.5, y: pt.y - lr * 2.5, width: lr * 5, height: lr * 5)
            NSBezierPath(ovalIn: glowRect).fill()
            // Core dot
            NSColor.red.setFill()
            let dotRect = CGRect(x: pt.x - lr, y: pt.y - lr, width: lr * 2, height: lr * 2)
            NSBezierPath(ovalIn: dotRect).fill()
        }

        // Click animations — expanding ring on click
        if !clickAnims.isEmpty {
            let now = Date()
            var remaining: [ClickAnimation] = []
            for anim in clickAnims {
                let elapsed = now.timeIntervalSince(anim.startTime)
                if elapsed >= clickAnimDuration { continue }
                let progress = CGFloat(elapsed / clickAnimDuration)
                let radius = clickAnimMaxRadius * progress
                let alpha = 0.6 * (1.0 - progress)
                let animColor = anim.isRightClick ? NSColor.systemBlue : engine.currentColor
                animColor.withAlphaComponent(alpha).setStroke()
                let animRect = CGRect(x: anim.point.x - radius, y: anim.point.y - radius, width: radius * 2, height: radius * 2)
                let animPath = NSBezierPath(ovalIn: animRect)
                animPath.lineWidth = 2.0
                animPath.stroke()
                remaining.append(anim)
            }
            clickAnims = remaining
        }

        // Screenshot selection rectangle
        if let region = engine.screenshotRegion {
            let x = min(region.0.x, region.1.x)
            let y = min(region.0.y, region.1.y)
            let w = abs(region.1.x - region.0.x)
            let h = abs(region.1.y - region.0.y)
            if w > 1 && h > 1 {
                NSColor.black.withAlphaComponent(0.3).setFill()
                dirtyRect.fill()
                NSColor.clear.setFill()
                CGRect(x: x, y: y, width: w, height: h).fill()
                NSColor.white.setStroke()
                let selPath = NSBezierPath(rect: CGRect(x: x, y: y, width: w, height: h))
                selPath.lineWidth = 2.0
                let pattern: [CGFloat] = [6.0, 4.0]
                selPath.setLineDash(pattern, count: 2, phase: 0)
                selPath.stroke()
            }
        }
    }

    // MARK: - Fade Timer

    func startFadeTimer() {
        guard fadeTimer == nil else { return }
        fadeTimer = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            let hasFading = self.engine.strokes.contains { $0.tool == .fadingInk && $0.createdAt != nil }
            if hasFading {
                self.needsDisplay = true
            } else {
                self.stopFadeTimer()
            }
        }
    }

    func stopFadeTimer() {
        fadeTimer?.invalidate()
        fadeTimer = nil
    }

    // MARK: - Click Animation Timer

    func startAnimTimer() {
        guard animTimer == nil else { return }
        animTimer = Timer.scheduledTimer(withTimeInterval: 0.02, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            let now = Date()
            self.clickAnims = self.clickAnims.filter { now.timeIntervalSince($0.startTime) < clickAnimDuration }
            if self.clickAnims.isEmpty {
                self.stopAnimTimer()
            }
            self.needsDisplay = true
        }
    }

    func stopAnimTimer() {
        animTimer?.invalidate()
        animTimer = nil
    }

    // MARK: - Key Events

    override func keyDown(with event: NSEvent) {
        if let handler = onKeyEvent, handler(event) {
            return
        }
        super.keyDown(with: event)
    }

    // MARK: - Trackpad Touch Events

    override func touchesBegan(with event: NSEvent) {
        guard trackpadDrawMode && isDrawingEnabled else {
            super.touchesBegan(with: event)
            return
        }
        trackpadTouchCount = event.touches(matching: .touching, in: self).count
        if trackpadTouchCount == 1 && !isTrackpadDrawing {
            // Single finger: begin drawing at current cursor position
            let point = currentCursorPoint(from: event)
            if engine.currentTool == .text {
                onTextRequested?(point)
            } else {
                let pressure = event.pressure > 0 ? CGFloat(event.pressure) : 1.0
                engine.beginStroke(at: point, pressure: pressure)
                isTrackpadDrawing = true
                needsDisplay = true
            }
        } else if trackpadTouchCount >= 2 && isTrackpadDrawing {
            // Second finger added: end the current stroke
            finishTrackpadStroke()
        }
    }

    override func touchesMoved(with event: NSEvent) {
        guard trackpadDrawMode && isDrawingEnabled else {
            super.touchesMoved(with: event)
            return
        }
        trackpadTouchCount = event.touches(matching: .touching, in: self).count
    }

    override func touchesEnded(with event: NSEvent) {
        guard trackpadDrawMode && isDrawingEnabled else {
            super.touchesEnded(with: event)
            return
        }
        trackpadTouchCount = event.touches(matching: .touching, in: self).count
        if trackpadTouchCount == 0 && isTrackpadDrawing {
            finishTrackpadStroke()
        }
    }

    override func touchesCancelled(with event: NSEvent) {
        guard trackpadDrawMode && isDrawingEnabled else {
            super.touchesCancelled(with: event)
            return
        }
        trackpadTouchCount = 0
        if isTrackpadDrawing {
            finishTrackpadStroke()
        }
    }

    private func finishTrackpadStroke() {
        let wasFading = engine.currentStroke?.tool == .fadingInk
        _ = engine.endStroke()
        if wasFading { startFadeTimer() }
        isTrackpadDrawing = false
        needsDisplay = true
        onStrokeChanged?()
    }

    private func currentCursorPoint(from event: NSEvent) -> CGPoint {
        return convert(event.locationInWindow, from: nil)
    }

    // MARK: - Mouse Events

    override func mouseMoved(with event: NSEvent) {
        let point = convert(event.locationInWindow, from: nil)

        // Trackpad draw mode: 1 finger touching = draw at cursor
        if trackpadDrawMode && isDrawingEnabled && isTrackpadDrawing && trackpadTouchCount == 1 {
            let pressure = event.pressure > 0 ? CGFloat(event.pressure) : 1.0
            engine.continueStroke(to: point, pressure: pressure)
            cursorPoint = point
            needsDisplay = true
            return
        }

        let needsTrack = cursorHighlightEnabled || spotlightEnabled || zoomEnabled || laserPointerEnabled
        if needsTrack {
            cursorPoint = point
            needsDisplay = true
        }
    }

    override func mouseDown(with event: NSEvent) {
        window?.makeKey()
        window?.makeFirstResponder(self)

        let point = convert(event.locationInWindow, from: nil)

        // Click animation
        if clickAnimationsEnabled {
            clickAnims.append(ClickAnimation(point: point, startTime: Date(), isRightClick: false))
            startAnimTimer()
        }

        // In trackpad draw mode, clicks are ignored for drawing (touch handles it)
        if trackpadDrawMode && isDrawingEnabled {
            return
        }

        guard isDrawingEnabled else {
            super.mouseDown(with: event)
            return
        }
        let pressure = getPressure(from: event)

        if engine.currentTool == .text {
            onTextRequested?(point)
            return
        }

        engine.beginStroke(at: point, pressure: pressure)
        needsDisplay = true
    }

    override func rightMouseDown(with event: NSEvent) {
        if clickAnimationsEnabled {
            let point = convert(event.locationInWindow, from: nil)
            clickAnims.append(ClickAnimation(point: point, startTime: Date(), isRightClick: true))
            startAnimTimer()
        }
    }

    override func mouseDragged(with event: NSEvent) {
        // In trackpad draw mode, drawing is handled via touch + mouseMoved
        if trackpadDrawMode && isDrawingEnabled { return }

        guard isDrawingEnabled else {
            super.mouseDragged(with: event)
            return
        }
        let point = convert(event.locationInWindow, from: nil)
        let pressure = getPressure(from: event)

        let needsTrack = cursorHighlightEnabled || spotlightEnabled || zoomEnabled || laserPointerEnabled
        if needsTrack {
            cursorPoint = point
        }

        engine.continueStroke(to: point, pressure: pressure)
        needsDisplay = true
    }

    override func mouseUp(with event: NSEvent) {
        // In trackpad draw mode, stroke end is handled by touchesEnded
        if trackpadDrawMode && isDrawingEnabled { return }

        guard isDrawingEnabled else {
            super.mouseUp(with: event)
            return
        }

        if engine.currentTool == .text && engine.currentStroke == nil {
            return
        }

        let wasFading = engine.currentStroke?.tool == .fadingInk
        _ = engine.endStroke()
        if wasFading {
            startFadeTimer()
        }
        needsDisplay = true
        onStrokeChanged?()
    }

    // MARK: - Pressure

    private func getPressure(from event: NSEvent) -> CGFloat {
        let pressure = event.pressure
        return pressure > 0 ? CGFloat(pressure) : 1.0
    }

    // MARK: - Actions

    func undo() {
        engine.undo()
        needsDisplay = true
        onStrokeChanged?()
    }

    func redo() {
        engine.redo()
        needsDisplay = true
        onStrokeChanged?()
    }

    func clearAll() {
        engine.clearAll()
        needsDisplay = true
        onStrokeChanged?()
    }

    func setTool(_ tool: DrawingTool) {
        engine.currentTool = tool
    }

    func setColor(_ color: NSColor) {
        engine.currentColor = color
    }

    func setLineWidth(_ width: CGFloat) {
        engine.currentLineWidth = width
    }
}
