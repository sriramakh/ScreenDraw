#!/usr/bin/env python3
"""
ScreenDraw - Live Screen Drawing Overlay for macOS
Draw over your screen during presentations and demos.
Inspired by Epic Pen — includes pen, highlighter, shapes, text,
screenshot, whiteboard/blackboard, pressure sensitivity, and more.
"""

import objc
import math
import os
import time
import datetime
from Foundation import NSURL, NSTimer
from AppKit import (
    NSApplication,
    NSApp,
    NSWindow,
    NSView,
    NSPanel,
    NSColor,
    NSBezierPath,
    NSScreen,
    NSEvent,
    NSStatusBar,
    NSMenu,
    NSMenuItem,
    NSImage,
    NSImageSymbolConfiguration,
    NSFont,
    NSTextField,
    NSButton,
    NSSlider,
    NSBox,
    NSCursor,
    NSVisualEffectView,
    NSPasteboard,
    NSBitmapImageRep,
    NSApplicationActivationPolicyAccessory,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskFullSizeContentView,
    NSWindowStyleMaskNonactivatingPanel,
    NSBackingStoreBuffered,
    NSScreenSaverWindowLevel,
    NSStatusWindowLevel,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSTextAlignmentCenter,
    NSLineCapStyleRound,
    NSLineJoinStyleRound,
    NSBezelStyleRegularSquare,
    NSControlSizeSmall,
    NSKeyDownMask,
    NSCommandKeyMask,
    NSShiftKeyMask,
    NSTrackingArea,
)
import Quartz

# Load AVFoundation for screen recording
_AVFoundation = objc.loadBundle(
    'AVFoundation', globals(),
    bundle_path='/System/Library/Frameworks/AVFoundation.framework'
)


# ============================================================
# Drawing Tool Types
# ============================================================

TOOL_PEN = "pen"
TOOL_HIGHLIGHTER = "highlighter"
TOOL_ARROW = "arrow"
TOOL_LINE = "line"
TOOL_RECTANGLE = "rectangle"
TOOL_CIRCLE = "circle"
TOOL_TEXT = "text"
TOOL_ERASER = "eraser"
TOOL_FADING_INK = "fading_ink"
TOOL_SCREENSHOT = "screenshot"

ALL_TOOLS = [
    TOOL_PEN, TOOL_HIGHLIGHTER, TOOL_LINE, TOOL_ARROW,
    TOOL_RECTANGLE, TOOL_CIRCLE, TOOL_TEXT, TOOL_ERASER,
    TOOL_FADING_INK,
]

TOOL_LABELS = {
    TOOL_PEN: "Pen",
    TOOL_HIGHLIGHTER: "Highlighter",
    TOOL_LINE: "Line",
    TOOL_ARROW: "Arrow",
    TOOL_RECTANGLE: "Rectangle",
    TOOL_CIRCLE: "Circle",
    TOOL_TEXT: "Text",
    TOOL_ERASER: "Eraser",
    TOOL_FADING_INK: "Fading Ink",
    TOOL_SCREENSHOT: "Screenshot",
}

TOOL_SYMBOLS = {
    TOOL_PEN: "pencil.tip",
    TOOL_HIGHLIGHTER: "highlighter",
    TOOL_LINE: "line.diagonal",
    TOOL_ARROW: "arrow.up.right",
    TOOL_RECTANGLE: "rectangle",
    TOOL_CIRCLE: "circle",
    TOOL_TEXT: "textformat",
    TOOL_ERASER: "eraser",
    TOOL_FADING_INK: "wand.and.rays",
    TOOL_SCREENSHOT: "camera.viewfinder",
}

# Expanded 16-color palette
COLORS = [
    (NSColor.systemRedColor(), "Red"),
    (NSColor.systemOrangeColor(), "Orange"),
    (NSColor.systemYellowColor(), "Yellow"),
    (NSColor.systemGreenColor(), "Green"),
    (NSColor.systemTealColor(), "Teal"),
    (NSColor.systemBlueColor(), "Blue"),
    (NSColor.systemIndigoColor(), "Indigo"),
    (NSColor.systemPurpleColor(), "Purple"),
    (NSColor.systemPinkColor(), "Pink"),
    (NSColor.systemBrownColor(), "Brown"),
    (NSColor.whiteColor(), "White"),
    (NSColor.lightGrayColor(), "Light Gray"),
    (NSColor.grayColor(), "Gray"),
    (NSColor.darkGrayColor(), "Dark Gray"),
    (NSColor.blackColor(), "Black"),
    (NSColor.cyanColor(), "Cyan"),
]

# Whiteboard/Blackboard modes
BOARD_NONE = "none"
BOARD_WHITE = "whiteboard"
BOARD_BLACK = "blackboard"

FADING_INK_DURATION = 3.0  # seconds before fading ink fully disappears

# Cursor highlight shapes
CURSOR_SHAPE_CIRCLE = "circle"
CURSOR_SHAPE_RING = "ring"
CURSOR_SHAPE_SQUIRCLE = "squircle"
CURSOR_SHAPES = [CURSOR_SHAPE_CIRCLE, CURSOR_SHAPE_RING, CURSOR_SHAPE_SQUIRCLE]

# Spotlight
SPOTLIGHT_RADIUS_DEFAULT = 120.0
SPOTLIGHT_DIM_ALPHA = 0.65

# Zoom
ZOOM_FACTOR_DEFAULT = 2.5
ZOOM_LENS_RADIUS = 120.0

# Laser pointer
LASER_POINTER_RADIUS = 6.0

# Click animation
CLICK_ANIM_DURATION = 0.35  # seconds
CLICK_ANIM_MAX_RADIUS = 30.0


# ============================================================
# Stroke Model
# ============================================================

class Stroke:
    def __init__(self, tool=TOOL_PEN, color=None, line_width=3.0, opacity=1.0,
                 text_content="", font_size=24.0):
        self.points = []
        self.tool = tool
        self.color = color or NSColor.redColor()
        self.line_width = line_width
        self.opacity = opacity
        self.pressures = []  # per-point pressure values (0.0-1.0)
        # Text tool properties
        self.text_content = text_content
        self.font_size = font_size
        self.created_at = None  # timestamp for fading ink


# ============================================================
# Drawing Engine
# ============================================================

class DrawingEngine:
    def __init__(self):
        self.strokes = []
        self.current_stroke = None
        self.undone_strokes = []
        self.current_tool = TOOL_PEN
        self.current_color = NSColor.systemRedColor()
        self.current_line_width = 3.0
        self.current_font_size = 24.0
        self.board_mode = BOARD_NONE  # whiteboard/blackboard
        self.screenshot_region = None  # (start, end) tuple for screenshot selection

    def begin_stroke(self, point, pressure=1.0):
        opacity = 1.0
        line_width = self.current_line_width

        if self.current_tool == TOOL_HIGHLIGHTER:
            opacity = 0.35
            line_width = max(line_width, 20.0)
        elif self.current_tool == TOOL_FADING_INK:
            pass  # fading ink uses normal pen width; opacity handled at draw time
        elif self.current_tool == TOOL_ERASER:
            line_width = max(line_width, 20.0)
        elif self.current_tool == TOOL_SCREENSHOT:
            self.screenshot_region = (point, point)
            return
        elif self.current_tool == TOOL_TEXT:
            # Text tool: single click places text; stroke is created at end
            pass

        color = NSColor.clearColor() if self.current_tool == TOOL_ERASER else self.current_color
        self.current_stroke = Stroke(
            tool=self.current_tool,
            color=color,
            line_width=line_width,
            opacity=opacity,
            font_size=self.current_font_size,
        )
        self.current_stroke.points.append(point)
        self.current_stroke.pressures.append(pressure)

        # Erase at the initial click point
        if self.current_tool == TOOL_ERASER:
            self._erase_at_point(point)

    def continue_stroke(self, point, pressure=1.0):
        if self.current_tool == TOOL_SCREENSHOT:
            if self.screenshot_region:
                self.screenshot_region = (self.screenshot_region[0], point)
            return

        if self.current_stroke:
            self.current_stroke.points.append(point)
            self.current_stroke.pressures.append(pressure)
            # Real-time erasing: remove strokes as the eraser passes over them
            if self.current_stroke.tool == TOOL_ERASER:
                self._erase_at_point(point)

    def end_stroke(self):
        if self.current_tool == TOOL_SCREENSHOT:
            # Screenshot handled by delegate, not stored as stroke
            return

        if self.current_stroke:
            if self.current_stroke.tool == TOOL_FADING_INK:
                self.current_stroke.created_at = time.time()
            if self.current_stroke.tool == TOOL_TEXT:
                # For text, a single click is enough (1 point)
                if len(self.current_stroke.points) >= 1:
                    self.strokes.append(self.current_stroke)
                    self.undone_strokes.clear()
            elif len(self.current_stroke.points) >= 2:
                if self.current_stroke.tool == TOOL_ERASER:
                    self._erase_strokes(self.current_stroke)
                else:
                    self.strokes.append(self.current_stroke)
                self.undone_strokes.clear()
        self.current_stroke = None

    def add_text_stroke(self, text, position):
        """Add a completed text stroke at the given position."""
        stroke = Stroke(
            tool=TOOL_TEXT,
            color=self.current_color,
            line_width=self.current_line_width,
            font_size=self.current_font_size,
            text_content=text,
        )
        stroke.points.append(position)
        self.strokes.append(stroke)
        self.undone_strokes.clear()

    def _erase_at_point(self, point):
        """Remove any stroke that has a point within eraser radius of the given point."""
        if not self.current_stroke:
            return
        eraser_radius = self.current_stroke.line_width / 2.0
        self.strokes = [
            s for s in self.strokes
            if not self._stroke_hit_test(s, point, eraser_radius)
        ]

    def _erase_strokes(self, eraser_stroke):
        """Remove any strokes intersecting with the eraser stroke path."""
        eraser_radius = eraser_stroke.line_width / 2.0
        self.strokes = [
            s for s in self.strokes
            if not any(
                self._stroke_hit_test(s, ep, eraser_radius)
                for ep in eraser_stroke.points
            )
        ]

    @staticmethod
    def _stroke_hit_test(stroke, point, eraser_radius):
        """Check if any point of the stroke is within eraser_radius of point."""
        threshold = eraser_radius + stroke.line_width / 2.0
        threshold_sq = threshold * threshold
        px, py = point[0], point[1]
        for sp in stroke.points:
            dx = px - sp[0]
            dy = py - sp[1]
            if dx * dx + dy * dy <= threshold_sq:
                return True
        return False

    def undo(self):
        if self.strokes:
            self.undone_strokes.append(self.strokes.pop())

    def redo(self):
        if self.undone_strokes:
            self.strokes.append(self.undone_strokes.pop())

    def clear_all(self):
        self.strokes.clear()
        self.undone_strokes.clear()
        self.current_stroke = None

    def draw_all(self, board_mode=BOARD_NONE):
        """Render all strokes. board_mode is drawn by the view's drawRect."""
        now = time.time()
        # Prune fully faded strokes
        self.strokes = [
            s for s in self.strokes
            if s.tool != TOOL_FADING_INK or s.created_at is None
            or (now - s.created_at) < FADING_INK_DURATION
        ]
        for stroke in self.strokes:
            self._draw_stroke(stroke, now)
        if self.current_stroke:
            self._draw_stroke(self.current_stroke, now)

    def _draw_stroke(self, stroke, now=None):
        if stroke.tool == TOOL_TEXT:
            self._draw_text(stroke)
            return

        if len(stroke.points) < 2:
            return

        # Set opacity
        opacity = stroke.opacity
        if stroke.tool == TOOL_FADING_INK and stroke.created_at is not None and now is not None:
            elapsed = now - stroke.created_at
            fade = max(0.0, 1.0 - elapsed / FADING_INK_DURATION)
            opacity = fade
            if opacity <= 0:
                return
        color = stroke.color.colorWithAlphaComponent_(opacity) if opacity < 1.0 else stroke.color

        if stroke.tool == TOOL_ERASER:
            # Eraser strokes are not rendered; they remove intersecting strokes
            return

        elif stroke.tool in (TOOL_PEN, TOOL_HIGHLIGHTER, TOOL_FADING_INK):
            self._draw_pen_stroke(stroke, color)

        elif stroke.tool == TOOL_LINE:
            color.setStroke()
            start = stroke.points[0]
            end = stroke.points[-1]
            path = NSBezierPath.bezierPath()
            path.setLineWidth_(stroke.line_width)
            path.setLineCapStyle_(NSLineCapStyleRound)
            path.moveToPoint_(start)
            path.lineToPoint_(end)
            path.stroke()

        elif stroke.tool == TOOL_ARROW:
            color.setStroke()
            color.setFill()
            start = stroke.points[0]
            end = stroke.points[-1]

            # Line
            path = NSBezierPath.bezierPath()
            path.setLineWidth_(stroke.line_width)
            path.setLineCapStyle_(NSLineCapStyleRound)
            path.moveToPoint_(start)
            path.lineToPoint_(end)
            path.stroke()

            # Arrowhead
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            head_length = max(15.0, stroke.line_width * 5)
            head_angle = math.pi / 6

            p1 = (
                end[0] - head_length * math.cos(angle - head_angle),
                end[1] - head_length * math.sin(angle - head_angle),
            )
            p2 = (
                end[0] - head_length * math.cos(angle + head_angle),
                end[1] - head_length * math.sin(angle + head_angle),
            )

            arrow = NSBezierPath.bezierPath()
            arrow.moveToPoint_(end)
            arrow.lineToPoint_(p1)
            arrow.lineToPoint_(p2)
            arrow.closePath()
            arrow.fill()

        elif stroke.tool == TOOL_RECTANGLE:
            color.setStroke()
            start = stroke.points[0]
            end = stroke.points[-1]
            x = min(start[0], end[0])
            y = min(start[1], end[1])
            w = abs(end[0] - start[0])
            h = abs(end[1] - start[1])
            path = NSBezierPath.bezierPathWithRect_(((x, y), (w, h)))
            path.setLineWidth_(stroke.line_width)
            path.stroke()

        elif stroke.tool == TOOL_CIRCLE:
            color.setStroke()
            start = stroke.points[0]
            end = stroke.points[-1]
            x = min(start[0], end[0])
            y = min(start[1], end[1])
            w = abs(end[0] - start[0])
            h = abs(end[1] - start[1])
            path = NSBezierPath.bezierPathWithOvalInRect_(((x, y), (w, h)))
            path.setLineWidth_(stroke.line_width)
            path.stroke()

    def _draw_pen_stroke(self, stroke, color):
        """Draw pen/highlighter with optional pressure sensitivity."""
        pts = stroke.points
        pressures = stroke.pressures
        has_pressure = len(pressures) == len(pts) and any(p != 1.0 for p in pressures)

        if has_pressure and len(pts) >= 2:
            # Variable-width stroke based on pressure
            for i in range(len(pts) - 1):
                seg_color = color
                seg_color.setStroke()
                p = pressures[i] if i < len(pressures) else 1.0
                width = stroke.line_width * (0.3 + 0.7 * p)
                path = NSBezierPath.bezierPath()
                path.setLineWidth_(width)
                path.setLineCapStyle_(NSLineCapStyleRound)
                path.moveToPoint_(pts[i])
                path.lineToPoint_(pts[i + 1])
                path.stroke()
        else:
            color.setStroke()
            path = NSBezierPath.bezierPath()
            path.setLineWidth_(stroke.line_width)
            path.setLineCapStyle_(NSLineCapStyleRound)
            path.setLineJoinStyle_(NSLineJoinStyleRound)
            path.moveToPoint_(pts[0])

            if len(pts) == 2:
                path.lineToPoint_(pts[1])
            else:
                for i in range(1, len(pts) - 1):
                    mid_x = (pts[i][0] + pts[i + 1][0]) / 2.0
                    mid_y = (pts[i][1] + pts[i + 1][1]) / 2.0
                    path.curveToPoint_controlPoint1_controlPoint2_(
                        (mid_x, mid_y), pts[i], pts[i]
                    )
                path.lineToPoint_(pts[-1])
            path.stroke()

    def _draw_text(self, stroke):
        """Render a text stroke."""
        if not stroke.text_content or not stroke.points:
            return
        point = stroke.points[0]
        color = stroke.color
        font = NSFont.systemFontOfSize_(stroke.font_size)
        from Foundation import NSString, NSFontAttributeName, NSForegroundColorAttributeName
        attrs = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: color,
        }
        ns_str = NSString.stringWithString_(stroke.text_content)
        ns_str.drawAtPoint_withAttributes_(point, attrs)


# ============================================================
# Drawing View
# ============================================================

class DrawingView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(DrawingView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.engine = DrawingEngine()
        self.is_drawing_enabled = True
        self.on_screenshot_taken = None  # callback: (start, end) -> None
        self.on_text_requested = None   # callback: (point) -> None
        self.on_key_event = None        # callback: (event) -> bool (True = handled)
        self.cursor_highlight_enabled = False
        self.cursor_highlight_radius = 30.0
        self.cursor_highlight_shape = CURSOR_SHAPE_CIRCLE  # circle, ring, squircle
        self._cursor_point = None  # current mouse position for highlight
        self._fade_timer = None

        # Spotlight mode
        self.spotlight_enabled = False
        self.spotlight_radius = SPOTLIGHT_RADIUS_DEFAULT

        # Zoom mode
        self.zoom_enabled = False
        self.zoom_factor = ZOOM_FACTOR_DEFAULT

        # Laser pointer
        self.laser_pointer_enabled = False

        # Click animations
        self.click_animations_enabled = False
        self._click_anims = []  # list of (point, start_time, is_right_click)
        self._anim_timer = None
        self.setWantsLayer_(True)
        self.layer().setBackgroundColor_(NSColor.clearColor().CGColor())
        return self

    def acceptsFirstResponder(self):
        return True

    def becomeFirstResponder(self):
        return True

    def keyDown_(self, event):
        """Direct key handler — always works when overlay window is key."""
        if self.on_key_event and self.on_key_event(event):
            return
        objc.super(DrawingView, self).keyDown_(event)

    def isFlipped(self):
        return False

    def drawRect_(self, rect):
        # Whiteboard/blackboard background
        if self.engine.board_mode == BOARD_WHITE:
            NSColor.whiteColor().set()
            NSBezierPath.fillRect_(rect)
        elif self.engine.board_mode == BOARD_BLACK:
            NSColor.blackColor().set()
            NSBezierPath.fillRect_(rect)
        else:
            NSColor.clearColor().set()
            NSBezierPath.fillRect_(rect)

        self.engine.draw_all()

        # Spotlight mode — dim everything except a circle around the cursor
        if self.spotlight_enabled and self._cursor_point is not None:
            cx, cy = self._cursor_point
            sr = self.spotlight_radius
            # Fill entire view with dim overlay
            NSColor.blackColor().colorWithAlphaComponent_(SPOTLIGHT_DIM_ALPHA).setFill()
            NSBezierPath.fillRect_(rect)
            # Cut out the spotlight circle (clear compositing)
            context = Quartz.CGContextGetCurrentContext() if hasattr(Quartz, 'CGContextGetCurrentContext') else None
            try:
                from AppKit import NSGraphicsContext
                context = NSGraphicsContext.currentContext().CGContext()
            except Exception:
                context = None
            if context:
                Quartz.CGContextSetBlendMode(context, Quartz.kCGBlendModeClear)
                spotlight_path = NSBezierPath.bezierPathWithOvalInRect_(
                    ((cx - sr, cy - sr), (sr * 2, sr * 2))
                )
                NSColor.clearColor().setFill()
                spotlight_path.fill()
                Quartz.CGContextSetBlendMode(context, Quartz.kCGBlendModeNormal)

        # Zoom lens — magnified view of area around cursor
        if self.zoom_enabled and self._cursor_point is not None:
            cx, cy = self._cursor_point
            zr = ZOOM_LENS_RADIUS
            zf = self.zoom_factor
            try:
                from AppKit import NSGraphicsContext
                context = NSGraphicsContext.currentContext().CGContext()
                Quartz.CGContextSaveGState(context)
                # Clip to lens circle
                lens_path = NSBezierPath.bezierPathWithOvalInRect_(
                    ((cx - zr, cy - zr), (zr * 2, zr * 2))
                )
                lens_path.addClip()
                # Translate so cursor is at center, then scale
                Quartz.CGContextTranslateCTM(context, cx, cy)
                Quartz.CGContextScaleCTM(context, zf, zf)
                Quartz.CGContextTranslateCTM(context, -cx, -cy)
                # Redraw strokes in zoomed context
                self.engine.draw_all()
                Quartz.CGContextRestoreGState(context)
                # Draw lens border
                NSColor.whiteColor().colorWithAlphaComponent_(0.8).setStroke()
                border_path = NSBezierPath.bezierPathWithOvalInRect_(
                    ((cx - zr, cy - zr), (zr * 2, zr * 2))
                )
                border_path.setLineWidth_(2.5)
                border_path.stroke()
            except Exception:
                pass

        # Draw cursor highlight
        if self.cursor_highlight_enabled and self._cursor_point is not None:
            cx, cy = self._cursor_point
            r = self.cursor_highlight_radius
            shape = self.cursor_highlight_shape

            if shape == CURSOR_SHAPE_SQUIRCLE:
                # Rounded rectangle (squircle)
                squircle_rect = ((cx - r, cy - r), (r * 2, r * 2))
                corner_radius = r * 0.35
                self.engine.current_color.colorWithAlphaComponent_(0.25).setFill()
                sq_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                    squircle_rect, corner_radius, corner_radius
                )
                sq_path.fill()
                self.engine.current_color.colorWithAlphaComponent_(0.5).setStroke()
                sq_path.setLineWidth_(1.5)
                sq_path.stroke()

            elif shape == CURSOR_SHAPE_RING:
                # Ring only (no fill)
                ring_path = NSBezierPath.bezierPathWithOvalInRect_(
                    ((cx - r, cy - r), (r * 2, r * 2))
                )
                self.engine.current_color.colorWithAlphaComponent_(0.6).setStroke()
                ring_path.setLineWidth_(3.0)
                ring_path.stroke()

            else:  # CURSOR_SHAPE_CIRCLE (default filled circle)
                highlight_color = self.engine.current_color.colorWithAlphaComponent_(0.25)
                highlight_color.setFill()
                highlight_path = NSBezierPath.bezierPathWithOvalInRect_(
                    ((cx - r, cy - r), (r * 2, r * 2))
                )
                highlight_path.fill()
                self.engine.current_color.colorWithAlphaComponent_(0.5).setStroke()
                highlight_path.setLineWidth_(1.5)
                highlight_path.stroke()

        # Laser pointer — small bright dot at cursor
        if self.laser_pointer_enabled and self._cursor_point is not None:
            cx, cy = self._cursor_point
            lr = LASER_POINTER_RADIUS
            # Glow
            NSColor.redColor().colorWithAlphaComponent_(0.3).setFill()
            glow_path = NSBezierPath.bezierPathWithOvalInRect_(
                ((cx - lr * 2.5, cy - lr * 2.5), (lr * 5, lr * 5))
            )
            glow_path.fill()
            # Core dot
            NSColor.redColor().setFill()
            dot_path = NSBezierPath.bezierPathWithOvalInRect_(
                ((cx - lr, cy - lr), (lr * 2, lr * 2))
            )
            dot_path.fill()

        # Click animations
        if self._click_anims:
            now = time.time()
            remaining = []
            for (pt, start_time, is_right) in self._click_anims:
                elapsed = now - start_time
                if elapsed >= CLICK_ANIM_DURATION:
                    continue
                progress = elapsed / CLICK_ANIM_DURATION
                radius = CLICK_ANIM_MAX_RADIUS * progress
                alpha = 0.6 * (1.0 - progress)
                anim_color = NSColor.systemBlueColor() if is_right else self.engine.current_color
                anim_color.colorWithAlphaComponent_(alpha).setStroke()
                anim_path = NSBezierPath.bezierPathWithOvalInRect_(
                    ((pt[0] - radius, pt[1] - radius), (radius * 2, radius * 2))
                )
                anim_path.setLineWidth_(2.0)
                anim_path.stroke()
                remaining.append((pt, start_time, is_right))
            self._click_anims = remaining

        # Draw screenshot selection rectangle
        if self.engine.screenshot_region:
            start, end = self.engine.screenshot_region
            x = min(start[0], end[0])
            y = min(start[1], end[1])
            w = abs(end[0] - start[0])
            h = abs(end[1] - start[1])
            if w > 1 and h > 1:
                # Semi-transparent overlay outside selection
                NSColor.blackColor().colorWithAlphaComponent_(0.3).set()
                NSBezierPath.fillRect_(rect)
                # Clear the selection area
                NSColor.clearColor().set()
                NSBezierPath.fillRect_(((x, y), (w, h)))
                # Dashed border around selection
                NSColor.whiteColor().setStroke()
                sel_path = NSBezierPath.bezierPathWithRect_(((x, y), (w, h)))
                sel_path.setLineWidth_(2.0)
                pattern = (6.0, 4.0)
                sel_path.setLineDash_count_phase_(pattern, 2, 0)
                sel_path.stroke()

    def _get_pressure(self, event):
        """Extract pen pressure from event. Returns 1.0 for mouse input."""
        try:
            pressure = event.pressure()
            if pressure > 0:
                return pressure
        except Exception:
            pass
        return 1.0

    def startFadeTimer(self):
        """Start a periodic timer to redraw fading ink strokes."""
        if self._fade_timer is not None:
            return
        self._fade_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, self, b"_fadeTimerFired:", None, True
        )

    def stopFadeTimer(self):
        """Stop the fading ink redraw timer."""
        if self._fade_timer is not None:
            self._fade_timer.invalidate()
            self._fade_timer = None

    @objc.IBAction
    def _fadeTimerFired_(self, timer):
        """Redraw to animate fading ink."""
        has_fading = any(
            s.tool == TOOL_FADING_INK and s.created_at is not None
            for s in self.engine.strokes
        )
        if has_fading:
            self.setNeedsDisplay_(True)
        else:
            self.stopFadeTimer()

    def _startAnimTimer(self):
        """Start a timer to animate click ripples."""
        if self._anim_timer is not None:
            return
        self._anim_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.02, self, b"_animTimerFired:", None, True
        )

    def _stopAnimTimer(self):
        if self._anim_timer is not None:
            self._anim_timer.invalidate()
            self._anim_timer = None

    @objc.IBAction
    def _animTimerFired_(self, timer):
        """Redraw click animations."""
        now = time.time()
        self._click_anims = [
            a for a in self._click_anims if (now - a[1]) < CLICK_ANIM_DURATION
        ]
        if self._click_anims:
            self.setNeedsDisplay_(True)
        else:
            self._stopAnimTimer()
            self.setNeedsDisplay_(True)

    def mouseMoved_(self, event):
        """Track mouse position for cursor highlight, spotlight, zoom, laser."""
        needs_track = (self.cursor_highlight_enabled or self.spotlight_enabled
                       or self.zoom_enabled or self.laser_pointer_enabled)
        if needs_track:
            self._cursor_point = self.convertPoint_fromView_(event.locationInWindow(), None)
            self.setNeedsDisplay_(True)

    def mouseDown_(self, event):
        # Re-assert key window and first responder so keyboard shortcuts work
        self.window().makeKeyWindow()
        self.window().makeFirstResponder_(self)

        point = self.convertPoint_fromView_(event.locationInWindow(), None)

        # Click animation (fires regardless of drawing state)
        if self.click_animations_enabled:
            self._click_anims.append((point, time.time(), False))
            self._startAnimTimer()

        if not self.is_drawing_enabled:
            return

        pressure = self._get_pressure(event)

        if self.engine.current_tool == TOOL_TEXT:
            # Text tool: request text input at click location
            if self.on_text_requested:
                self.on_text_requested(point)
            return

        self.engine.begin_stroke(point, pressure)
        self.setNeedsDisplay_(True)

    def rightMouseDown_(self, event):
        """Right-click animation (blue ring)."""
        if self.click_animations_enabled:
            point = self.convertPoint_fromView_(event.locationInWindow(), None)
            self._click_anims.append((point, time.time(), True))
            self._startAnimTimer()

    def mouseDragged_(self, event):
        if not self.is_drawing_enabled:
            return
        point = self.convertPoint_fromView_(event.locationInWindow(), None)
        pressure = self._get_pressure(event)

        if self.engine.current_tool == TOOL_SCREENSHOT:
            self.engine.continue_stroke(point, pressure)
            self.setNeedsDisplay_(True)
            return

        if self.engine.current_stroke is None:
            return
        self.engine.continue_stroke(point, pressure)
        self.setNeedsDisplay_(True)

    def mouseUp_(self, event):
        if not self.is_drawing_enabled:
            return

        if self.engine.current_tool == TOOL_SCREENSHOT:
            if self.engine.screenshot_region and self.on_screenshot_taken:
                start, end = self.engine.screenshot_region
                self.on_screenshot_taken(start, end)
            self.engine.screenshot_region = None
            self.setNeedsDisplay_(True)
            return

        if self.engine.current_stroke is None:
            return
        was_fading = self.engine.current_stroke.tool == TOOL_FADING_INK
        self.engine.end_stroke()
        if was_fading:
            self.startFadeTimer()
        self.setNeedsDisplay_(True)


# ============================================================
# Overlay Window
# ============================================================

class OverlayWindow(NSWindow):
    def initWithScreen_(self, screen):
        frame = screen.frame()
        self = objc.super(OverlayWindow, self).initWithContentRect_styleMask_backing_defer_screen_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
            screen,
        )
        if self is None:
            return None

        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.clearColor())
        self.setLevel_(NSScreenSaverWindowLevel)
        self.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        self.setIgnoresMouseEvents_(False)
        self.setHasShadow_(False)
        self.setReleasedWhenClosed_(False)
        self.setAcceptsMouseMovedEvents_(True)
        self.setSharingType_(0)  # NSWindowSharingNone — hidden from screen sharing
        return self

    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return True


# ============================================================
# Tooltip Window (renders above all overlay levels)
# ============================================================

class TooltipWindow(NSWindow):
    """A small borderless window that displays tooltip text above all other windows."""
    _instance = None

    @classmethod
    def shared(cls):
        if cls._instance is None:
            cls._instance = cls.alloc().init()
        return cls._instance

    def init(self):
        self = objc.super(TooltipWindow, self).initWithContentRect_styleMask_backing_defer_(
            ((0, 0), (200, 24)),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        if self is None:
            return None
        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.clearColor())
        self.setLevel_(NSScreenSaverWindowLevel + 2)
        self.setIgnoresMouseEvents_(True)
        self.setHasShadow_(True)
        self.setReleasedWhenClosed_(False)
        self.setSharingType_(0)  # NSWindowSharingNone — hidden from screen sharing

        # Label
        self._label = NSTextField.labelWithString_("")
        self._label.setFont_(NSFont.systemFontOfSize_(11))
        self._label.setTextColor_(NSColor.whiteColor())
        self._label.setAlignment_(NSTextAlignmentCenter)
        self._label.setWantsLayer_(True)
        self._label.layer().setBackgroundColor_(
            NSColor.blackColor().colorWithAlphaComponent_(0.85).CGColor()
        )
        self._label.layer().setCornerRadius_(5)
        self._label.setFrame_(((0, 0), (200, 24)))
        self.contentView().addSubview_(self._label)
        return self

    def showTooltip_atPoint_(self, text, screen_point):
        if not text:
            self.orderOut_(None)
            return
        self._label.setStringValue_(text)
        self._label.sizeToFit()
        label_frame = self._label.frame()
        padding = 12
        w = label_frame.size.width + padding
        h = 24
        # Position to the left of the toolbar
        x = screen_point[0] - w - 8
        y = screen_point[1] - h / 2
        self.setFrame_display_(((x, y), (w, h)), True)
        self._label.setFrame_(((0, 0), (w, h)))
        self.orderFront_(None)

    def hide(self):
        self.orderOut_(None)


# ============================================================
# Toolbar Panel
# ============================================================

class ToolbarPanel(NSPanel):
    def initWithDelegate_(self, delegate):
        screen_frame = NSScreen.mainScreen().visibleFrame()
        panel_width = 56
        total_height = 1120

        panel_rect = (
            (screen_frame.origin.x + screen_frame.size.width - panel_width - 16,
             screen_frame.origin.y + screen_frame.size.height / 2 - total_height / 2),
            (panel_width, total_height),
        )

        self = objc.super(ToolbarPanel, self).initWithContentRect_styleMask_backing_defer_(
            panel_rect,
            NSWindowStyleMaskNonactivatingPanel | NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskFullSizeContentView,
            NSBackingStoreBuffered,
            False,
        )
        if self is None:
            return None

        self._toolbar_delegate = delegate
        self._tool_buttons = []
        self._color_buttons = []
        self._all_buttons = []  # all buttons for tooltip lookup
        self._button_tooltips = {}  # id(btn) -> tooltip text
        self._selected_tool_index = 0
        self._selected_color_index = 0
        self._drawing_toggle_btn = None
        self._whiteboard_btn = None
        self._blackboard_btn = None
        self._record_btn = None
        self._cursor_highlight_btn = None
        self._cursor_shape_btn = None
        self._spotlight_btn = None
        self._zoom_btn = None
        self._laser_btn = None
        self._click_anim_btn = None
        self._size_slider = None
        self._tooltip_window = TooltipWindow.shared()
        self._hover_timer = None

        self.setFloatingPanel_(True)
        self.setLevel_(NSScreenSaverWindowLevel + 1)
        self.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.clearColor())
        self.setSharingType_(0)  # NSWindowSharingNone — hidden from screen sharing
        self.setTitleVisibility_(1)  # NSWindowTitleHidden
        self.setTitlebarAppearsTransparent_(True)
        self.setMovableByWindowBackground_(True)
        self.setHasShadow_(True)
        self.setBecomesKeyOnlyIfNeeded_(True)
        self.setAcceptsMouseMovedEvents_(True)

        self._setup_ui()
        return self

    def _setup_ui(self):
        content = self.contentView()
        frame = content.bounds()

        # Visual effect background
        effect_view = NSVisualEffectView.alloc().initWithFrame_(frame)
        effect_view.setAutoresizingMask_(1 | 2 | 4 | 8 | 16 | 32)
        effect_view.setMaterial_(15)  # hudWindow
        effect_view.setBlendingMode_(1)  # behindWindow
        effect_view.setState_(1)  # active
        effect_view.setWantsLayer_(True)
        effect_view.layer().setCornerRadius_(14)
        effect_view.layer().setMasksToBounds_(True)
        self.setContentView_(effect_view)

        button_size = 32
        color_btn_size = 20
        y_offset = frame.size.height - 16
        center_x = frame.size.width / 2

        def add_button(symbol_name, tooltip, action_name, tint_color=None, tag=0):
            nonlocal y_offset
            btn = NSButton.alloc().initWithFrame_(((center_x - button_size / 2, y_offset - button_size + 2), (button_size, button_size - 2)))
            image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol_name, tooltip)
            if image:
                config = NSImageSymbolConfiguration.configurationWithPointSize_weight_(13, 5)
                configured_image = image.imageWithSymbolConfiguration_(config)
                if configured_image:
                    btn.setImage_(configured_image)
            else:
                btn.setTitle_(tooltip[:2])
            btn.setBordered_(False)
            btn.setBezelStyle_(NSBezelStyleRegularSquare)
            btn.setTag_(tag)
            btn.setWantsLayer_(True)
            btn.layer().setCornerRadius_(7)
            if tint_color:
                btn.setContentTintColor_(tint_color)
            btn.setTarget_(self)
            btn.setAction_(action_name)
            effect_view.addSubview_(btn)
            self._all_buttons.append(btn)
            self._button_tooltips[id(btn)] = tooltip
            y_offset -= button_size
            return btn

        def add_separator():
            nonlocal y_offset
            y_offset -= 3
            sep = NSBox.alloc().initWithFrame_(((8, y_offset), (frame.size.width - 16, 1)))
            sep.setBoxType_(2)
            effect_view.addSubview_(sep)
            y_offset -= 4

        def add_label(text):
            nonlocal y_offset
            label = NSTextField.labelWithString_(text)
            label.setFont_(NSFont.systemFontOfSize_weight_(7, 0.4))
            label.setTextColor_(NSColor.secondaryLabelColor())
            label.setAlignment_(NSTextAlignmentCenter)
            label_width = frame.size.width - 8
            label.setFrame_(((4, y_offset - 10), (label_width, 10)))
            effect_view.addSubview_(label)
            y_offset -= 12

        # Drawing toggle
        self._drawing_toggle_btn = add_button("pencil.circle.fill", "Toggle Drawing (D)", b"toggleDrawing:", tint_color=NSColor.systemGreenColor())

        add_separator()

        # Tools
        add_label("Tools")
        for i, tool in enumerate(ALL_TOOLS):
            btn = add_button(TOOL_SYMBOLS[tool], TOOL_LABELS[tool], b"toolSelected:", tag=i)
            self._tool_buttons.append(btn)

        self._update_tool_selection()

        add_separator()

        # Screenshot button (separate from tools)
        add_button(TOOL_SYMBOLS[TOOL_SCREENSHOT], "Screenshot (S)", b"screenshotAction:", tint_color=NSColor.systemBlueColor())

        add_separator()

        # Colors — 16-color grid (2 columns of 8)
        add_label("Color")
        col_size = color_btn_size
        col_gap = 2
        total_w = col_size * 2 + col_gap
        left_x = center_x - total_w / 2
        for i, (color, name) in enumerate(COLORS):
            col = i % 2
            row = i // 2
            x = left_x + col * (col_size + col_gap)
            y = y_offset - (row + 1) * (col_size + 1)
            btn = NSButton.alloc().initWithFrame_(((x, y), (col_size, col_size)))
            btn.setBordered_(False)
            btn.setTitle_("")
            btn.setTag_(i)
            btn.setWantsLayer_(True)
            btn.layer().setCornerRadius_(col_size / 2)
            btn.layer().setBackgroundColor_(color.CGColor())
            if name in ("White", "Yellow", "Light Gray", "Cyan"):
                btn.layer().setBorderColor_(NSColor.grayColor().colorWithAlphaComponent_(0.5).CGColor())
                btn.layer().setBorderWidth_(1)
            btn.setTarget_(self)
            btn.setAction_(b"colorSelected:")
            btn.setToolTip_(name)
            effect_view.addSubview_(btn)
            self._color_buttons.append(btn)

        num_rows = (len(COLORS) + 1) // 2
        y_offset -= num_rows * (col_size + 1) + 2

        self._update_color_selection()

        add_separator()

        # Size slider
        add_label("Size")
        slider = NSSlider.alloc().initWithFrame_(((center_x - 14, y_offset - 55), (28, 55)))
        slider.setMinValue_(1.0)
        slider.setMaxValue_(20.0)
        slider.setDoubleValue_(3.0)
        slider.setTarget_(self)
        slider.setAction_(b"sizeChanged:")
        slider.setControlSize_(NSControlSizeSmall)
        slider.setVertical_(True)
        effect_view.addSubview_(slider)
        self._size_slider = slider
        y_offset -= 60

        add_separator()

        # Whiteboard / Blackboard
        add_label("Board")
        self._whiteboard_btn = add_button("rectangle.fill", "Whiteboard (W)", b"whiteboardAction:")
        self._whiteboard_btn.setContentTintColor_(NSColor.lightGrayColor())
        self._blackboard_btn = add_button("rectangle.fill", "Blackboard (B)", b"blackboardAction:")
        self._blackboard_btn.setContentTintColor_(NSColor.darkGrayColor())

        self._cursor_highlight_btn = add_button("target", "Cursor Highlight (H)", b"cursorHighlightAction:")
        self._cursor_highlight_btn.setContentTintColor_(NSColor.systemYellowColor())

        self._cursor_shape_btn = add_button("circle.dashed", "Cursor Shape (Shift+H)", b"cursorShapeAction:")
        self._cursor_shape_btn.setContentTintColor_(NSColor.systemYellowColor())

        self._spotlight_btn = add_button("light.max", "Spotlight (F)", b"spotlightAction:")
        self._spotlight_btn.setContentTintColor_(NSColor.systemOrangeColor())

        self._zoom_btn = add_button("magnifyingglass", "Zoom Lens (Z)", b"zoomAction:")
        self._zoom_btn.setContentTintColor_(NSColor.systemIndigoColor())

        self._laser_btn = add_button("smallcircle.filled.circle", "Laser Pointer (L)", b"laserAction:")
        self._laser_btn.setContentTintColor_(NSColor.systemRedColor())

        self._click_anim_btn = add_button("circle.circle", "Click Animations (K)", b"clickAnimAction:")
        self._click_anim_btn.setContentTintColor_(NSColor.systemPinkColor())

        add_separator()

        # Action buttons
        add_button("arrow.uturn.backward", "Undo (Cmd+Z)", b"undoAction:")
        add_button("arrow.uturn.forward", "Redo (Cmd+Shift+Z)", b"redoAction:")
        add_button("trash", "Clear All (C)", b"clearAction:", tint_color=NSColor.systemRedColor())

        add_separator()

        self._record_btn = add_button("record.circle", "Record Screen (R)", b"recordAction:", tint_color=NSColor.systemRedColor())

        add_separator()

        add_button("minus.circle.fill", "Minimize (M)", b"minimizeAction:", tint_color=NSColor.systemOrangeColor())
        add_button("xmark.circle.fill", "Quit (Esc / Cmd+Q)", b"quitAction:", tint_color=NSColor.systemGrayColor())

        # Add mouse tracking to the entire effect view for custom tooltips
        tracking_area = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            effect_view.bounds(),
            0x02 | 0x20 | 0x08 | 0x01,  # MouseMoved | ActiveAlways | InVisibleRect | MouseEnteredAndExited
            self,
            None,
        )
        effect_view.addTrackingArea_(tracking_area)

    def _update_tool_selection(self):
        for i, btn in enumerate(self._tool_buttons):
            if i == self._selected_tool_index:
                btn.layer().setBackgroundColor_(
                    NSColor.controlAccentColor().colorWithAlphaComponent_(0.3).CGColor()
                )
            else:
                btn.layer().setBackgroundColor_(NSColor.clearColor().CGColor())

    def _update_color_selection(self):
        for i, btn in enumerate(self._color_buttons):
            if i == self._selected_color_index:
                btn.layer().setBorderColor_(NSColor.controlAccentColor().CGColor())
                btn.layer().setBorderWidth_(2.5)
            else:
                _, name = COLORS[i]
                if name in ("White", "Yellow", "Light Gray", "Cyan"):
                    btn.layer().setBorderColor_(NSColor.grayColor().colorWithAlphaComponent_(0.5).CGColor())
                    btn.layer().setBorderWidth_(1)
                else:
                    btn.layer().setBorderWidth_(0)

    def mouseMoved_(self, event):
        """Show custom tooltip for the button under the cursor."""
        loc = event.locationInWindow()
        view = self.contentView()
        local_point = view.convertPoint_fromView_(loc, None)
        for btn in self._all_buttons:
            f = btn.frame()
            if (f.origin.x <= local_point[0] <= f.origin.x + f.size.width and
                    f.origin.y <= local_point[1] <= f.origin.y + f.size.height):
                tip = self._button_tooltips.get(id(btn))
                if tip:
                    screen_pt = self.convertPointToScreen_(loc)
                    self._tooltip_window.showTooltip_atPoint_(tip, screen_pt)
                    return
        self._tooltip_window.hide()

    def mouseExited_(self, event):
        self._tooltip_window.hide()

    def update_drawing_toggle(self, is_enabled):
        if self._drawing_toggle_btn:
            if is_enabled:
                self._drawing_toggle_btn.setContentTintColor_(NSColor.systemGreenColor())
                self._button_tooltips[id(self._drawing_toggle_btn)] = "Drawing ON (D to toggle)"
            else:
                self._drawing_toggle_btn.setContentTintColor_(NSColor.systemGrayColor())
                self._button_tooltips[id(self._drawing_toggle_btn)] = "Drawing OFF (D to toggle)"

    def update_record_button(self, is_recording):
        if self._record_btn:
            if is_recording:
                self._record_btn.setContentTintColor_(NSColor.systemRedColor())
                self._button_tooltips[id(self._record_btn)] = "Stop Recording (R)"
                self._record_btn.layer().setBackgroundColor_(
                    NSColor.systemRedColor().colorWithAlphaComponent_(0.2).CGColor())
            else:
                self._record_btn.setContentTintColor_(NSColor.systemRedColor())
                self._button_tooltips[id(self._record_btn)] = "Record Screen (R)"
                self._record_btn.layer().setBackgroundColor_(NSColor.clearColor().CGColor())

    def update_cursor_highlight_button(self, is_enabled):
        if self._cursor_highlight_btn:
            if is_enabled:
                self._cursor_highlight_btn.layer().setBackgroundColor_(
                    NSColor.systemYellowColor().colorWithAlphaComponent_(0.3).CGColor())
                self._button_tooltips[id(self._cursor_highlight_btn)] = "Cursor Highlight ON (H)"
            else:
                self._cursor_highlight_btn.layer().setBackgroundColor_(NSColor.clearColor().CGColor())
                self._button_tooltips[id(self._cursor_highlight_btn)] = "Cursor Highlight (H)"

    def update_spotlight_button(self, is_enabled):
        if self._spotlight_btn:
            if is_enabled:
                self._spotlight_btn.layer().setBackgroundColor_(
                    NSColor.systemOrangeColor().colorWithAlphaComponent_(0.3).CGColor())
            else:
                self._spotlight_btn.layer().setBackgroundColor_(NSColor.clearColor().CGColor())

    def update_zoom_button(self, is_enabled):
        if self._zoom_btn:
            if is_enabled:
                self._zoom_btn.layer().setBackgroundColor_(
                    NSColor.systemIndigoColor().colorWithAlphaComponent_(0.3).CGColor())
            else:
                self._zoom_btn.layer().setBackgroundColor_(NSColor.clearColor().CGColor())

    def update_laser_button(self, is_enabled):
        if self._laser_btn:
            if is_enabled:
                self._laser_btn.layer().setBackgroundColor_(
                    NSColor.systemRedColor().colorWithAlphaComponent_(0.2).CGColor())
            else:
                self._laser_btn.layer().setBackgroundColor_(NSColor.clearColor().CGColor())

    def update_click_anim_button(self, is_enabled):
        if self._click_anim_btn:
            if is_enabled:
                self._click_anim_btn.layer().setBackgroundColor_(
                    NSColor.systemPinkColor().colorWithAlphaComponent_(0.3).CGColor())
            else:
                self._click_anim_btn.layer().setBackgroundColor_(NSColor.clearColor().CGColor())

    def update_cursor_shape_button(self, shape_name):
        if self._cursor_shape_btn:
            self._button_tooltips[id(self._cursor_shape_btn)] = f"Cursor Shape: {shape_name} (Shift+H)"

    def update_board_buttons(self, board_mode):
        if self._whiteboard_btn:
            if board_mode == BOARD_WHITE:
                self._whiteboard_btn.layer().setBackgroundColor_(
                    NSColor.controlAccentColor().colorWithAlphaComponent_(0.3).CGColor())
            else:
                self._whiteboard_btn.layer().setBackgroundColor_(NSColor.clearColor().CGColor())
        if self._blackboard_btn:
            if board_mode == BOARD_BLACK:
                self._blackboard_btn.layer().setBackgroundColor_(
                    NSColor.controlAccentColor().colorWithAlphaComponent_(0.3).CGColor())
            else:
                self._blackboard_btn.layer().setBackgroundColor_(NSColor.clearColor().CGColor())

    # Actions
    @objc.IBAction
    def toolSelected_(self, sender):
        self._selected_tool_index = sender.tag()
        self._update_tool_selection()
        self._toolbar_delegate.on_tool_selected(ALL_TOOLS[sender.tag()])

    @objc.IBAction
    def colorSelected_(self, sender):
        self._selected_color_index = sender.tag()
        self._update_color_selection()
        self._toolbar_delegate.on_color_selected(COLORS[sender.tag()][0])

    @objc.IBAction
    def sizeChanged_(self, sender):
        self._toolbar_delegate.on_line_width_changed(sender.doubleValue())

    @objc.IBAction
    def screenshotAction_(self, sender):
        self._toolbar_delegate.on_screenshot()

    @objc.IBAction
    def whiteboardAction_(self, sender):
        self._toolbar_delegate.on_whiteboard()

    @objc.IBAction
    def blackboardAction_(self, sender):
        self._toolbar_delegate.on_blackboard()

    @objc.IBAction
    def cursorHighlightAction_(self, sender):
        self._toolbar_delegate.on_cursor_highlight()

    @objc.IBAction
    def cursorShapeAction_(self, sender):
        self._toolbar_delegate.on_cursor_shape()

    @objc.IBAction
    def spotlightAction_(self, sender):
        self._toolbar_delegate.on_spotlight()

    @objc.IBAction
    def zoomAction_(self, sender):
        self._toolbar_delegate.on_zoom()

    @objc.IBAction
    def laserAction_(self, sender):
        self._toolbar_delegate.on_laser()

    @objc.IBAction
    def clickAnimAction_(self, sender):
        self._toolbar_delegate.on_click_anim()

    @objc.IBAction
    def undoAction_(self, sender):
        self._toolbar_delegate.on_undo()

    @objc.IBAction
    def redoAction_(self, sender):
        self._toolbar_delegate.on_redo()

    @objc.IBAction
    def clearAction_(self, sender):
        self._toolbar_delegate.on_clear()

    @objc.IBAction
    def toggleDrawing_(self, sender):
        self._toolbar_delegate.on_toggle_drawing()

    @objc.IBAction
    def recordAction_(self, sender):
        self._toolbar_delegate.on_record()

    @objc.IBAction
    def minimizeAction_(self, sender):
        self._toolbar_delegate.on_minimize()

    @objc.IBAction
    def quitAction_(self, sender):
        self._tooltip_window.hide()
        self._toolbar_delegate.on_quit()


# ============================================================
# App Delegate
# ============================================================

class AppDelegate(NSView):  # Using NSView as base for ObjC compatibility
    """Main application controller."""

    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self.overlay_window = None
        self.drawing_view = None
        self.toolbar_panel = None
        self.status_item = None
        self.is_drawing_active = True
        self._text_input_field = None
        self._text_input_point = None
        self._text_just_committed = False
        self._is_recording = False
        self._capture_session = None
        self._movie_output = None
        self._recording_path = None
        return self

    def applicationDidFinishLaunching_(self, notification):
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self._setup_status_bar()
        self._setup_overlay_window()
        self._setup_toolbar()
        self._setup_keyboard_shortcuts()
        self._activate_drawing()

    def _setup_status_bar(self):
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-2)
        button = self.status_item.button()
        if button:
            image = NSImage.imageWithSystemSymbolName_accessibilityDescription_("pencil.tip.crop.circle", "ScreenDraw")
            if image:
                config = NSImageSymbolConfiguration.configurationWithPointSize_weight_(16, 5)
                configured = image.imageWithSymbolConfiguration_(config)
                if configured:
                    button.setImage_(configured)
            else:
                button.setTitle_("SD")

        menu = NSMenu.alloc().init()

        toggle_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Toggle Drawing (D)", b"toggleDrawingMode:", "d")
        toggle_item.setTarget_(self)
        menu.addItem_(toggle_item)

        restore_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Show/Hide (M)", b"restoreFromMenu:", "m")
        restore_item.setTarget_(self)
        menu.addItem_(restore_item)

        record_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Record Screen (R)", b"recordFromMenu:", "r")
        record_item.setTarget_(self)
        menu.addItem_(record_item)

        menu.addItem_(NSMenuItem.separatorItem())

        undo_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Undo", b"undoAction:", "z")
        undo_item.setTarget_(self)
        menu.addItem_(undo_item)

        redo_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Redo", b"redoAction:", "Z")
        redo_item.setTarget_(self)
        menu.addItem_(redo_item)

        clear_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Clear All", b"clearAction:", "")
        clear_item.setTarget_(self)
        menu.addItem_(clear_item)

        menu.addItem_(NSMenuItem.separatorItem())

        for i, tool in enumerate(ALL_TOOLS):
            key = str(i + 1) if i < 9 else ""
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                TOOL_LABELS[tool], b"selectToolFromMenu:", key
            )
            item.setTag_(i)
            item.setTarget_(self)
            menu.addItem_(item)

        menu.addItem_(NSMenuItem.separatorItem())

        screenshot_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Screenshot", b"screenshotFromMenu:", "s")
        screenshot_item.setTarget_(self)
        menu.addItem_(screenshot_item)

        menu.addItem_(NSMenuItem.separatorItem())

        wb_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Whiteboard", b"whiteboardFromMenu:", "w")
        wb_item.setTarget_(self)
        menu.addItem_(wb_item)

        bb_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Blackboard", b"blackboardFromMenu:", "b")
        bb_item.setTarget_(self)
        menu.addItem_(bb_item)

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit ScreenDraw", b"quitApp:", "q")
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        self.status_item.setMenu_(menu)

    def _setup_overlay_window(self):
        screen = NSScreen.mainScreen()
        self.overlay_window = OverlayWindow.alloc().initWithScreen_(screen)
        self.drawing_view = DrawingView.alloc().initWithFrame_(screen.frame())
        self.drawing_view.setAutoresizingMask_(1 | 2 | 4 | 8 | 16 | 32)
        self.drawing_view.on_screenshot_taken = self._handle_screenshot
        self.drawing_view.on_text_requested = self._handle_text_request
        self.drawing_view.on_key_event = self._handle_view_key_event
        self.overlay_window.setContentView_(self.drawing_view)
        self.overlay_window.makeKeyAndOrderFront_(None)
        self.overlay_window.makeFirstResponder_(self.drawing_view)

    def _setup_toolbar(self):
        self.toolbar_panel = ToolbarPanel.alloc().initWithDelegate_(self)
        self.toolbar_panel.orderFront_(None)

    def _setup_keyboard_shortcuts(self):
        # Local monitor handles events when our windows are key
        NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask,
            self._handle_key_event,
        )
        # Global monitor catches Escape/Cmd+Q even when we lose key focus
        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask,
            self._handle_global_key_event,
        )

    def _handle_view_key_event(self, event):
        """Called from DrawingView.keyDown_ — the most reliable path for keys."""
        return self._process_key_event(event)

    def _handle_global_key_event(self, event):
        """Global monitor — only handle quit shortcuts as a safety net."""
        flags = event.modifierFlags()
        has_cmd = bool(flags & NSCommandKeyMask)
        chars = event.charactersIgnoringModifiers()
        if event.keyCode() == 53:  # Escape
            NSApp.terminate_(None)
        elif has_cmd and chars == "q":
            NSApp.terminate_(None)

    def _handle_key_event(self, event):
        """Local monitor — returns None to swallow, event to pass through."""
        handled = self._process_key_event(event)
        return None if handled else event

    def _process_key_event(self, event):
        """Shared key processing. Returns True if handled, False otherwise."""
        # Guard: if text was just committed, swallow any stale events
        if self._text_just_committed:
            self._text_just_committed = False
            return True

        # If text input field is active, let it handle keys
        if self._text_input_field:
            key_code = event.keyCode()
            if key_code == 36:  # Return key — commit text
                self._commit_text_input()
                return True
            elif key_code == 53:  # Escape — cancel text input
                self._cancel_text_input()
                return True
            return False  # Let the text field handle other keys

        flags = event.modifierFlags()
        has_cmd = bool(flags & NSCommandKeyMask)
        has_shift = bool(flags & NSShiftKeyMask)
        chars = event.charactersIgnoringModifiers()

        if not chars:
            return False

        # Cmd+Z = Undo, Cmd+Shift+Z = Redo
        if has_cmd and chars == "z":
            if has_shift:
                self.drawing_view.engine.redo()
            else:
                self.drawing_view.engine.undo()
            self.drawing_view.setNeedsDisplay_(True)
            return True

        # Cmd+S = Screenshot
        if has_cmd and chars == "s":
            self._activate_screenshot_mode()
            return True

        # Cmd+Q = Quit
        if has_cmd and chars == "q":
            NSApp.terminate_(None)
            return True

        # Escape = Quit
        if event.keyCode() == 53:
            NSApp.terminate_(None)
            return True

        # No modifier keys for these
        if has_cmd:
            return False

        if chars == "d":
            self._toggle_drawing()
            return True
        elif chars == "1":
            self._set_tool(TOOL_PEN, 0)
            return True
        elif chars == "2":
            self._set_tool(TOOL_HIGHLIGHTER, 1)
            return True
        elif chars == "3":
            self._set_tool(TOOL_LINE, 2)
            return True
        elif chars == "4":
            self._set_tool(TOOL_ARROW, 3)
            return True
        elif chars == "5":
            self._set_tool(TOOL_RECTANGLE, 4)
            return True
        elif chars == "6":
            self._set_tool(TOOL_CIRCLE, 5)
            return True
        elif chars == "7":
            self._set_tool(TOOL_TEXT, 6)
            return True
        elif chars == "8":
            self._set_tool(TOOL_ERASER, 7)
            return True
        elif chars == "9":
            self._set_tool(TOOL_FADING_INK, 8)
            return True
        elif chars == "h":
            if has_shift:
                self._cycle_cursor_shape()
            else:
                self._toggle_cursor_highlight()
            return True
        elif chars == "f":
            self._toggle_spotlight()
            return True
        elif chars == "z":
            self._toggle_zoom()
            return True
        elif chars == "l":
            self._toggle_laser_pointer()
            return True
        elif chars == "k":
            self._toggle_click_animations()
            return True
        elif chars == "s":
            self._activate_screenshot_mode()
            return True
        elif chars == "w":
            self._toggle_whiteboard()
            return True
        elif chars == "b":
            self._toggle_blackboard()
            return True
        elif chars == "r":
            self._toggle_recording()
            return True
        elif chars == "m":
            self._minimize_app()
            return True
        elif chars == "c":
            self.drawing_view.engine.clear_all()
            self.drawing_view.setNeedsDisplay_(True)
            return True
        elif chars in ("[", "-"):
            w = max(1, self.drawing_view.engine.current_line_width - 1)
            self.drawing_view.engine.current_line_width = w
            return True
        elif chars in ("]", "=", "+"):
            w = min(30, self.drawing_view.engine.current_line_width + 1)
            self.drawing_view.engine.current_line_width = w
            return True

        return False

    def _set_tool(self, tool, index):
        self.drawing_view.engine.current_tool = tool
        if self.toolbar_panel:
            self.toolbar_panel._selected_tool_index = index
            self.toolbar_panel._update_tool_selection()

    # ---- Minimize / Hide ----

    def _minimize_app(self):
        """Hide the overlay and toolbar (minimize). Use status bar to restore."""
        self._deactivate_drawing()
        self.overlay_window.orderOut_(None)
        if self.toolbar_panel:
            self.toolbar_panel._tooltip_window.hide()
            self.toolbar_panel.orderOut_(None)

    def _restore_app(self):
        """Restore the overlay and toolbar from minimized state."""
        self.overlay_window.makeKeyAndOrderFront_(None)
        if self.toolbar_panel:
            self.toolbar_panel.orderFront_(None)
        self._activate_drawing()

    # ---- Cursor Highlight ----

    def _toggle_cursor_highlight(self):
        enabled = not self.drawing_view.cursor_highlight_enabled
        self.drawing_view.cursor_highlight_enabled = enabled
        if not enabled:
            self.drawing_view._cursor_point = None
            self.drawing_view.setNeedsDisplay_(True)
        if self.toolbar_panel:
            self.toolbar_panel.update_cursor_highlight_button(enabled)

    # ---- Spotlight ----

    def _toggle_spotlight(self):
        enabled = not self.drawing_view.spotlight_enabled
        self.drawing_view.spotlight_enabled = enabled
        if not enabled:
            self.drawing_view.setNeedsDisplay_(True)
        if self.toolbar_panel:
            self.toolbar_panel.update_spotlight_button(enabled)

    # ---- Zoom ----

    def _toggle_zoom(self):
        enabled = not self.drawing_view.zoom_enabled
        self.drawing_view.zoom_enabled = enabled
        if not enabled:
            self.drawing_view.setNeedsDisplay_(True)
        if self.toolbar_panel:
            self.toolbar_panel.update_zoom_button(enabled)

    # ---- Laser Pointer ----

    def _toggle_laser_pointer(self):
        enabled = not self.drawing_view.laser_pointer_enabled
        self.drawing_view.laser_pointer_enabled = enabled
        if not enabled:
            self.drawing_view.setNeedsDisplay_(True)
        if self.toolbar_panel:
            self.toolbar_panel.update_laser_button(enabled)

    # ---- Click Animations ----

    def _toggle_click_animations(self):
        enabled = not self.drawing_view.click_animations_enabled
        self.drawing_view.click_animations_enabled = enabled
        if self.toolbar_panel:
            self.toolbar_panel.update_click_anim_button(enabled)

    # ---- Cursor Shape ----

    def _cycle_cursor_shape(self):
        view = self.drawing_view
        current = view.cursor_highlight_shape
        idx = CURSOR_SHAPES.index(current) if current in CURSOR_SHAPES else 0
        new_idx = (idx + 1) % len(CURSOR_SHAPES)
        view.cursor_highlight_shape = CURSOR_SHAPES[new_idx]
        if view.cursor_highlight_enabled:
            view.setNeedsDisplay_(True)
        if self.toolbar_panel:
            self.toolbar_panel.update_cursor_shape_button(CURSOR_SHAPES[new_idx])

    # ---- Whiteboard / Blackboard ----

    def _toggle_whiteboard(self):
        engine = self.drawing_view.engine
        if engine.board_mode == BOARD_WHITE:
            engine.board_mode = BOARD_NONE
        else:
            engine.board_mode = BOARD_WHITE
        self.drawing_view.setNeedsDisplay_(True)
        if self.toolbar_panel:
            self.toolbar_panel.update_board_buttons(engine.board_mode)

    def _toggle_blackboard(self):
        engine = self.drawing_view.engine
        if engine.board_mode == BOARD_BLACK:
            engine.board_mode = BOARD_NONE
        else:
            engine.board_mode = BOARD_BLACK
        self.drawing_view.setNeedsDisplay_(True)
        if self.toolbar_panel:
            self.toolbar_panel.update_board_buttons(engine.board_mode)

    # ---- Screenshot ----

    def _activate_screenshot_mode(self):
        """Switch to screenshot tool so next drag captures a region."""
        self.drawing_view.engine.current_tool = TOOL_SCREENSHOT
        if self.toolbar_panel:
            # Deselect tool buttons since screenshot is separate
            self.toolbar_panel._selected_tool_index = -1
            self.toolbar_panel._update_tool_selection()

    def _handle_screenshot(self, start, end):
        """Capture the selected region of the screen."""
        x = min(start[0], end[0])
        y = min(start[1], end[1])
        w = abs(end[0] - start[0])
        h = abs(end[1] - start[1])

        if w < 5 or h < 5:
            # Revert to pen tool
            self._set_tool(TOOL_PEN, 0)
            return

        # Temporarily hide overlay and toolbar for clean capture
        self.overlay_window.orderOut_(None)
        self.toolbar_panel.orderOut_(None)

        # Small delay to let windows hide, then capture
        self._screenshot_rect = (x, y, w, h)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.15, self, b"_doScreenCapture:", None, False
        )

    @objc.IBAction
    def _doScreenCapture_(self, timer):
        """Perform the actual screen capture after windows are hidden."""
        x, y, w, h = self._screenshot_rect
        screen = NSScreen.mainScreen()
        screen_h = screen.frame().size.height

        # CGWindowListCreateImage uses top-left origin
        cg_rect = Quartz.CGRectMake(x, screen_h - y - h, w, h)
        cg_image = Quartz.CGWindowListCreateImage(
            cg_rect,
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID,
            Quartz.kCGWindowImageDefault,
        )

        if cg_image:
            # Copy to clipboard
            ns_image = NSImage.alloc().initWithCGImage_size_(cg_image, (w, h))
            pasteboard = NSPasteboard.generalPasteboard()
            pasteboard.clearContents()
            pasteboard.writeObjects_([ns_image])

            # Also save to Desktop
            bitmap_rep = NSBitmapImageRep.alloc().initWithCGImage_(cg_image)
            png_data = bitmap_rep.representationUsingType_properties_(4, None)  # NSBitmapImageFileTypePNG = 4
            if png_data:
                desktop = os.path.expanduser("~/Desktop")
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filepath = os.path.join(desktop, f"ScreenDraw_{timestamp}.png")
                png_data.writeToFile_atomically_(filepath, True)

        # Restore windows
        self.overlay_window.makeKeyAndOrderFront_(None)
        self.toolbar_panel.orderFront_(None)

        # Revert to pen tool
        self._set_tool(TOOL_PEN, 0)

    # ---- Screen Recording ----

    def _toggle_recording(self):
        """Start or stop screen recording."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start recording the screen using AVFoundation."""
        if self._is_recording:
            return

        try:
            session = AVCaptureSession.alloc().init()
            session.setSessionPreset_("AVCaptureSessionPresetHigh")

            # Screen input — capture the main display
            display_id = Quartz.CGMainDisplayID()
            screen_input = AVCaptureScreenInput.alloc().initWithDisplayID_(display_id)
            if screen_input is None:
                print("ScreenDraw: Failed to create screen capture input")
                return
            screen_input.setMinFrameDuration_((1, 30, 1, 0))  # CMTime tuple: 30 fps
            screen_input.setCapturesMouseClicks_(True)
            screen_input.setCapturesCursor_(True)

            if session.canAddInput_(screen_input):
                session.addInput_(screen_input)
            else:
                print("ScreenDraw: Cannot add screen input to session")
                return

            # Movie file output
            movie_output = AVCaptureMovieFileOutput.alloc().init()
            if session.canAddOutput_(movie_output):
                session.addOutput_(movie_output)
            else:
                print("ScreenDraw: Cannot add movie output to session")
                return

            # Output path
            desktop = os.path.expanduser("~/Desktop")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filepath = os.path.join(desktop, f"ScreenDraw_Recording_{timestamp}.mov")

            self._capture_session = session
            self._movie_output = movie_output
            self._recording_path = filepath

            session.startRunning()

            file_url = NSURL.fileURLWithPath_(filepath)
            movie_output.startRecordingToOutputFileURL_recordingDelegate_(file_url, self)

            self._is_recording = True
            if self.toolbar_panel:
                self.toolbar_panel.update_record_button(True)
            print(f"ScreenDraw: Recording started -> {filepath}")

        except Exception as e:
            print(f"ScreenDraw: Recording failed to start: {e}")
            self._is_recording = False

    def _stop_recording(self):
        """Stop the current screen recording."""
        if not self._is_recording:
            return

        try:
            if self._movie_output:
                self._movie_output.stopRecording()
        except Exception as e:
            print(f"ScreenDraw: Error stopping recording: {e}")

    # AVCaptureFileOutputRecordingDelegate methods
    def captureOutput_didFinishRecordingToOutputFileAtURL_fromConnections_error_(
        self, output, url, connections, error
    ):
        """Called when recording finishes."""
        if self._capture_session:
            self._capture_session.stopRunning()
        self._capture_session = None
        self._movie_output = None
        self._is_recording = False

        if self.toolbar_panel:
            self.toolbar_panel.update_record_button(False)

        if error:
            print(f"ScreenDraw: Recording error: {error}")
        else:
            path = url.path() if url else self._recording_path
            print(f"ScreenDraw: Recording saved to {path}")
        self._recording_path = None

    # ---- Text Input ----

    def _handle_text_request(self, point):
        """Show a text input field at the clicked point."""
        if self._text_input_field:
            self._cancel_text_input()

        self._text_input_point = point
        field_width = 300
        field_height = 30
        font_size = self.drawing_view.engine.current_font_size

        field = NSTextField.alloc().initWithFrame_(
            ((point[0], point[1] - field_height / 2), (field_width, field_height))
        )
        field.setFont_(NSFont.systemFontOfSize_(font_size))
        field.setTextColor_(self.drawing_view.engine.current_color)
        field.setDrawsBackground_(False)
        field.setBackgroundColor_(NSColor.clearColor())
        field.setBordered_(True)
        field.setEditable_(True)
        field.setSelectable_(True)
        field.setStringValue_("")
        field.setPlaceholderString_("Type text, press Enter")
        field.setTarget_(self)
        field.setAction_(b"textFieldAction:")

        self.drawing_view.addSubview_(field)
        self.overlay_window.makeFirstResponder_(field)
        self._text_input_field = field

    @objc.IBAction
    def textFieldAction_(self, sender):
        """Called when Enter is pressed in the text input field."""
        self._commit_text_input()

    def _commit_text_input(self):
        """Commit the text from the input field as a text stroke."""
        if not self._text_input_field:
            return
        self._text_just_committed = True
        text = self._text_input_field.stringValue()
        if text and self._text_input_point:
            self.drawing_view.engine.add_text_stroke(text, self._text_input_point)
        self._text_input_field.removeFromSuperview()
        self._text_input_field = None
        self._text_input_point = None
        self.drawing_view.setNeedsDisplay_(True)
        self.overlay_window.makeFirstResponder_(self.drawing_view)

    def _cancel_text_input(self):
        """Cancel text input without adding a stroke."""
        if self._text_input_field:
            self._text_input_field.removeFromSuperview()
            self._text_input_field = None
            self._text_input_point = None
            self.overlay_window.makeFirstResponder_(self.drawing_view)

    # ---- Drawing State ----

    def _activate_drawing(self):
        self.is_drawing_active = True
        self.drawing_view.is_drawing_enabled = True
        self.overlay_window.setIgnoresMouseEvents_(False)
        self.overlay_window.makeKeyAndOrderFront_(None)
        if self.toolbar_panel:
            self.toolbar_panel.update_drawing_toggle(True)
        NSCursor.crosshairCursor().set()

    def _deactivate_drawing(self):
        self.is_drawing_active = False
        self.drawing_view.is_drawing_enabled = False
        self.overlay_window.setIgnoresMouseEvents_(True)
        if self.toolbar_panel:
            self.toolbar_panel.update_drawing_toggle(False)
        NSCursor.arrowCursor().set()

    def _toggle_drawing(self):
        if self.is_drawing_active:
            self._deactivate_drawing()
        else:
            self._activate_drawing()

    # ---- Menu bar actions ----
    @objc.IBAction
    def toggleDrawingMode_(self, sender):
        self._toggle_drawing()

    @objc.IBAction
    def undoAction_(self, sender):
        self.drawing_view.engine.undo()
        self.drawing_view.setNeedsDisplay_(True)

    @objc.IBAction
    def redoAction_(self, sender):
        self.drawing_view.engine.redo()
        self.drawing_view.setNeedsDisplay_(True)

    @objc.IBAction
    def clearAction_(self, sender):
        self.drawing_view.engine.clear_all()
        self.drawing_view.setNeedsDisplay_(True)

    @objc.IBAction
    def selectToolFromMenu_(self, sender):
        idx = sender.tag()
        self._set_tool(ALL_TOOLS[idx], idx)

    @objc.IBAction
    def screenshotFromMenu_(self, sender):
        self._activate_screenshot_mode()

    @objc.IBAction
    def whiteboardFromMenu_(self, sender):
        self._toggle_whiteboard()

    @objc.IBAction
    def blackboardFromMenu_(self, sender):
        self._toggle_blackboard()

    @objc.IBAction
    def recordFromMenu_(self, sender):
        self._toggle_recording()

    @objc.IBAction
    def restoreFromMenu_(self, sender):
        if self.overlay_window.isVisible():
            self._minimize_app()
        else:
            self._restore_app()

    @objc.IBAction
    def quitApp_(self, sender):
        NSApp.terminate_(None)

    # ---- Toolbar delegate methods ----
    def on_tool_selected(self, tool):
        self.drawing_view.engine.current_tool = tool

    def on_color_selected(self, color):
        self.drawing_view.engine.current_color = color

    def on_line_width_changed(self, width):
        self.drawing_view.engine.current_line_width = width

    def on_screenshot(self):
        self._activate_screenshot_mode()

    def on_whiteboard(self):
        self._toggle_whiteboard()

    def on_blackboard(self):
        self._toggle_blackboard()

    def on_undo(self):
        self.drawing_view.engine.undo()
        self.drawing_view.setNeedsDisplay_(True)

    def on_redo(self):
        self.drawing_view.engine.redo()
        self.drawing_view.setNeedsDisplay_(True)

    def on_clear(self):
        self.drawing_view.engine.clear_all()
        self.drawing_view.setNeedsDisplay_(True)

    def on_toggle_drawing(self):
        self._toggle_drawing()

    def on_minimize(self):
        self._minimize_app()

    def on_cursor_highlight(self):
        self._toggle_cursor_highlight()

    def on_cursor_shape(self):
        self._cycle_cursor_shape()

    def on_spotlight(self):
        self._toggle_spotlight()

    def on_zoom(self):
        self._toggle_zoom()

    def on_laser(self):
        self._toggle_laser_pointer()

    def on_click_anim(self):
        self._toggle_click_animations()

    def on_record(self):
        self._toggle_recording()

    def on_quit(self):
        NSApp.terminate_(None)

    def applicationShouldTerminate_(self, sender):
        # Stop recording if active before quitting
        if self._is_recording:
            self._stop_recording()
        return True


# ============================================================
# Main
# ============================================================

def main():
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()
