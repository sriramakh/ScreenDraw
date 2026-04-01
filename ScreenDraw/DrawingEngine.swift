import Cocoa

// MARK: - Drawing Tool Types

enum DrawingTool: String, CaseIterable {
    case pointer = "Pointer"
    case pen = "Pen"
    case highlighter = "Highlighter"
    case line = "Line"
    case arrow = "Arrow"
    case rectangle = "Rectangle"
    case circle = "Circle"
    case text = "Text"
    case eraser = "Eraser"
    case fadingInk = "Fading Ink"

    static let allDrawingTools: [DrawingTool] = [.pointer, .pen, .highlighter, .line, .arrow, .rectangle, .circle, .text, .eraser, .fadingInk]

    var isDrawingTool: Bool {
        return self != .pointer
    }

    var symbolName: String {
        switch self {
        case .pointer: return "cursorarrow"
        case .pen: return "pencil.tip"
        case .highlighter: return "highlighter"
        case .line: return "line.diagonal"
        case .arrow: return "arrow.up.right"
        case .rectangle: return "rectangle"
        case .circle: return "circle"
        case .text: return "textformat"
        case .eraser: return "eraser"
        case .fadingInk: return "wand.and.rays"
        }
    }
}

// Board modes
enum BoardMode {
    case none, whiteboard, blackboard
}

// MARK: - Color Palette

let colorPalette: [(NSColor, String)] = [
    (.systemRed, "Red"),
    (.systemOrange, "Orange"),
    (.systemYellow, "Yellow"),
    (.systemGreen, "Green"),
    (.systemTeal, "Teal"),
    (.systemBlue, "Blue"),
    (.systemIndigo, "Indigo"),
    (.systemPurple, "Purple"),
    (.systemPink, "Pink"),
    (.systemBrown, "Brown"),
    (.white, "White"),
    (.lightGray, "Light Gray"),
    (.gray, "Gray"),
    (.darkGray, "Dark Gray"),
    (.black, "Black"),
    (.cyan, "Cyan"),
]

let fadingInkDuration: TimeInterval = 3.0

// Cursor highlight shapes
enum CursorHighlightShape: String, CaseIterable {
    case circle = "circle"
    case ring = "ring"
    case squircle = "squircle"
}

// Spotlight
let spotlightRadiusDefault: CGFloat = 120.0
let spotlightDimAlpha: CGFloat = 0.65

// Zoom
let zoomFactorDefault: CGFloat = 2.5
let zoomLensRadius: CGFloat = 120.0

// Laser pointer
let laserPointerRadius: CGFloat = 6.0

// Click animation
let clickAnimDuration: TimeInterval = 0.35
let clickAnimMaxRadius: CGFloat = 30.0

struct ClickAnimation {
    let point: CGPoint
    let startTime: Date
    let isRightClick: Bool
}

// MARK: - Stroke Model

struct Stroke {
    var points: [CGPoint]
    var pressures: [CGFloat]
    var color: NSColor
    var lineWidth: CGFloat
    var tool: DrawingTool
    var opacity: CGFloat
    var textContent: String
    var fontSize: CGFloat
    var createdAt: Date?

    init(points: [CGPoint] = [], color: NSColor = .red, lineWidth: CGFloat = 3.0,
         tool: DrawingTool = .pen, opacity: CGFloat = 1.0,
         textContent: String = "", fontSize: CGFloat = 24.0) {
        self.points = points
        self.pressures = []
        self.color = color
        self.lineWidth = lineWidth
        self.tool = tool
        self.opacity = opacity
        self.textContent = textContent
        self.fontSize = fontSize
        self.createdAt = nil
    }
}

// MARK: - Drawing Engine

class DrawingEngine {
    var strokes: [Stroke] = []
    var currentStroke: Stroke?
    var undoneStrokes: [Stroke] = []

    var currentTool: DrawingTool = .pen
    var currentColor: NSColor = .systemRed
    var currentLineWidth: CGFloat = 3.0
    var currentFontSize: CGFloat = 24.0
    var boardMode: BoardMode = .none
    var screenshotRegion: (CGPoint, CGPoint)?

    func beginStroke(at point: CGPoint, pressure: CGFloat = 1.0) {
        var opacity: CGFloat = 1.0
        var lineWidth = currentLineWidth

        switch currentTool {
        case .pointer:
            return // Pointer doesn't draw
        case .highlighter:
            opacity = 0.35
            lineWidth = max(lineWidth, 20.0)
        case .fadingInk:
            break
        case .eraser:
            lineWidth = max(lineWidth, 20.0)
        case .text:
            return
        default:
            break
        }

        currentStroke = Stroke(
            points: [point],
            color: currentTool == .eraser ? .clear : currentColor,
            lineWidth: lineWidth,
            tool: currentTool,
            opacity: opacity,
            fontSize: currentFontSize
        )
        currentStroke?.pressures.append(pressure)

        if currentTool == .eraser {
            eraseAtPoint(point)
        }
    }

    func continueStroke(to point: CGPoint, pressure: CGFloat = 1.0) {
        currentStroke?.points.append(point)
        currentStroke?.pressures.append(pressure)

        if currentStroke?.tool == .eraser {
            eraseAtPoint(point)
        }
    }

    private func eraseAtPoint(_ point: CGPoint) {
        guard let eraserStroke = currentStroke else { return }
        let eraserRadius = eraserStroke.lineWidth / 2.0
        strokes.removeAll { stroke in
            for strokePoint in stroke.points {
                let dx = point.x - strokePoint.x
                let dy = point.y - strokePoint.y
                let threshold = eraserRadius + stroke.lineWidth / 2.0
                if (dx * dx + dy * dy) <= threshold * threshold {
                    return true
                }
            }
            return false
        }
    }

    func endStroke() -> DrawingTool? {
        guard var stroke = currentStroke else {
            currentStroke = nil
            return nil
        }

        let tool = stroke.tool

        if stroke.tool == .fadingInk {
            stroke.createdAt = Date()
        }

        if stroke.tool == .text {
            if stroke.points.count >= 1 {
                strokes.append(stroke)
                undoneStrokes.removeAll()
            }
        } else if stroke.points.count >= 2 {
            if stroke.tool == .eraser {
                eraseStrokes(with: stroke)
            } else {
                strokes.append(stroke)
            }
            undoneStrokes.removeAll()
        }
        currentStroke = nil
        return tool
    }

    func addTextStroke(_ text: String, at position: CGPoint) {
        let stroke = Stroke(
            points: [position],
            color: currentColor,
            lineWidth: currentLineWidth,
            tool: .text,
            textContent: text,
            fontSize: currentFontSize
        )
        strokes.append(stroke)
        undoneStrokes.removeAll()
    }

    private func eraseStrokes(with eraserStroke: Stroke) {
        let eraserRadius = eraserStroke.lineWidth / 2.0
        strokes.removeAll { stroke in
            for eraserPoint in eraserStroke.points {
                for strokePoint in stroke.points {
                    let dx = eraserPoint.x - strokePoint.x
                    let dy = eraserPoint.y - strokePoint.y
                    let threshold = eraserRadius + stroke.lineWidth / 2.0
                    if (dx * dx + dy * dy) <= threshold * threshold {
                        return true
                    }
                }
            }
            return false
        }
    }

    func undo() {
        guard let last = strokes.popLast() else { return }
        undoneStrokes.append(last)
    }

    func redo() {
        guard let last = undoneStrokes.popLast() else { return }
        strokes.append(last)
    }

    func clearAll() {
        strokes.removeAll()
        undoneStrokes.removeAll()
        currentStroke = nil
    }

    // MARK: - Rendering

    func draw(in context: CGContext, dirtyRect: NSRect) {
        let now = Date()
        // Prune fully faded strokes
        strokes.removeAll { stroke in
            if stroke.tool == .fadingInk, let created = stroke.createdAt {
                return now.timeIntervalSince(created) >= fadingInkDuration
            }
            return false
        }

        for stroke in strokes {
            drawStroke(stroke, in: context, now: now)
        }
        if let current = currentStroke {
            drawStroke(current, in: context, now: now)
        }
    }

    private func drawStroke(_ stroke: Stroke, in context: CGContext, now: Date) {
        if stroke.tool == .text {
            drawText(stroke)
            return
        }

        guard stroke.points.count >= 2 else { return }

        context.saveGState()

        var opacity = stroke.opacity
        if stroke.tool == .fadingInk, let created = stroke.createdAt {
            let elapsed = now.timeIntervalSince(created)
            let fade = max(0.0, 1.0 - elapsed / fadingInkDuration)
            opacity = CGFloat(fade)
            if opacity <= 0 {
                context.restoreGState()
                return
            }
        }
        context.setAlpha(opacity)

        switch stroke.tool {
        case .eraser:
            break

        case .pen, .highlighter, .fadingInk:
            context.setStrokeColor(stroke.color.cgColor)
            context.setLineWidth(stroke.lineWidth)
            context.setLineCap(.round)
            context.setLineJoin(.round)
            drawSmoothedPath(stroke.points, in: context)

        case .line:
            context.setStrokeColor(stroke.color.cgColor)
            context.setLineWidth(stroke.lineWidth)
            context.setLineCap(.round)
            context.beginPath()
            context.move(to: stroke.points.first!)
            context.addLine(to: stroke.points.last!)
            context.strokePath()

        case .arrow:
            context.setStrokeColor(stroke.color.cgColor)
            context.setFillColor(stroke.color.cgColor)
            context.setLineWidth(stroke.lineWidth)
            context.setLineCap(.round)
            drawArrow(from: stroke.points.first!, to: stroke.points.last!, in: context, lineWidth: stroke.lineWidth)

        case .rectangle:
            context.setStrokeColor(stroke.color.cgColor)
            context.setLineWidth(stroke.lineWidth)
            let origin = stroke.points.first!
            let end = stroke.points.last!
            let rect = CGRect(
                x: min(origin.x, end.x),
                y: min(origin.y, end.y),
                width: abs(end.x - origin.x),
                height: abs(end.y - origin.y)
            )
            context.stroke(rect)

        case .circle:
            context.setStrokeColor(stroke.color.cgColor)
            context.setLineWidth(stroke.lineWidth)
            let origin = stroke.points.first!
            let end = stroke.points.last!
            let rect = CGRect(
                x: min(origin.x, end.x),
                y: min(origin.y, end.y),
                width: abs(end.x - origin.x),
                height: abs(end.y - origin.y)
            )
            context.strokeEllipse(in: rect)

        case .text:
            break // handled above
        }

        context.restoreGState()
    }

    private func drawText(_ stroke: Stroke) {
        guard let position = stroke.points.first, !stroke.textContent.isEmpty else { return }
        let attributes: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: stroke.fontSize),
            .foregroundColor: stroke.color
        ]
        let string = NSAttributedString(string: stroke.textContent, attributes: attributes)
        string.draw(at: position)
    }

    private func drawSmoothedPath(_ points: [CGPoint], in context: CGContext) {
        guard points.count >= 2 else { return }

        context.beginPath()
        context.move(to: points[0])

        if points.count == 2 {
            context.addLine(to: points[1])
        } else {
            for i in 1..<points.count - 1 {
                let midPoint = CGPoint(
                    x: (points[i].x + points[i + 1].x) / 2.0,
                    y: (points[i].y + points[i + 1].y) / 2.0
                )
                context.addQuadCurve(to: midPoint, control: points[i])
            }
            context.addLine(to: points.last!)
        }

        context.strokePath()
    }

    private func drawArrow(from start: CGPoint, to end: CGPoint, in context: CGContext, lineWidth: CGFloat) {
        let headLength: CGFloat = max(15.0, lineWidth * 5)
        let headAngle: CGFloat = CGFloat.pi / 6

        let angle = atan2(end.y - start.y, end.x - start.x)

        context.beginPath()
        context.move(to: start)
        context.addLine(to: end)
        context.strokePath()

        let arrowPoint1 = CGPoint(
            x: end.x - headLength * cos(angle - headAngle),
            y: end.y - headLength * sin(angle - headAngle)
        )
        let arrowPoint2 = CGPoint(
            x: end.x - headLength * cos(angle + headAngle),
            y: end.y - headLength * sin(angle + headAngle)
        )

        context.beginPath()
        context.move(to: end)
        context.addLine(to: arrowPoint1)
        context.addLine(to: arrowPoint2)
        context.closePath()
        context.fillPath()
    }
}
