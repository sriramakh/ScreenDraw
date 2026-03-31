#!/usr/bin/env python3
"""
ScreenDraw for Windows - Live Screen Drawing Overlay
Draw over your screen during presentations and demos.
Full feature parity with the macOS version.

Requirements: pip install pillow pystray keyboard pyautogui
Optional for screen recording: pip install opencv-python numpy
"""

import tkinter as tk
from tkinter import font as tkfont
import ctypes
import ctypes.wintypes
import math
import time
import os
import datetime
import threading
import sys
import json

# Windows API constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
WM_DISPLAYCHANGE = 0x007E

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

# ============================================================
# Drawing Tool Types
# ============================================================

TOOL_PEN = "pen"
TOOL_HIGHLIGHTER = "highlighter"
TOOL_LINE = "line"
TOOL_ARROW = "arrow"
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

TOOL_SHORTCUTS = {
    TOOL_PEN: "1",
    TOOL_HIGHLIGHTER: "2",
    TOOL_LINE: "3",
    TOOL_ARROW: "4",
    TOOL_RECTANGLE: "5",
    TOOL_CIRCLE: "6",
    TOOL_TEXT: "7",
    TOOL_ERASER: "8",
    TOOL_FADING_INK: "9",
}

# Expanded 16-color palette (hex)
COLORS = [
    ("#FF3B30", "Red"),
    ("#FF9500", "Orange"),
    ("#FFCC00", "Yellow"),
    ("#34C759", "Green"),
    ("#30B0C7", "Teal"),
    ("#007AFF", "Blue"),
    ("#5856D6", "Indigo"),
    ("#AF52DE", "Purple"),
    ("#FF2D55", "Pink"),
    ("#A2845E", "Brown"),
    ("#FFFFFF", "White"),
    ("#C7C7CC", "Light Gray"),
    ("#8E8E93", "Gray"),
    ("#48484A", "Dark Gray"),
    ("#000000", "Black"),
    ("#00FFFF", "Cyan"),
]

# Board modes
BOARD_NONE = "none"
BOARD_WHITE = "whiteboard"
BOARD_BLACK = "blackboard"

FADING_INK_DURATION = 3.0

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
CLICK_ANIM_DURATION = 0.35
CLICK_ANIM_MAX_RADIUS = 30.0


# ============================================================
# Stroke Model
# ============================================================

class Stroke:
    def __init__(self, tool=TOOL_PEN, color="#FF3B30", line_width=3.0, opacity=1.0,
                 text_content="", font_size=24.0):
        self.points = []  # list of (x, y) tuples
        self.tool = tool
        self.color = color
        self.line_width = line_width
        self.opacity = opacity
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
        self.current_color = COLORS[0][0]  # Red
        self.current_line_width = 3.0
        self.current_font_size = 24.0
        self.board_mode = BOARD_NONE
        self.screenshot_region = None

    def begin_stroke(self, point):
        opacity = 1.0
        line_width = self.current_line_width

        if self.current_tool == TOOL_HIGHLIGHTER:
            opacity = 0.35
            line_width = max(line_width, 20.0)
        elif self.current_tool == TOOL_ERASER:
            line_width = max(line_width, 20.0)
        elif self.current_tool == TOOL_SCREENSHOT:
            self.screenshot_region = (point, point)
            return
        elif self.current_tool == TOOL_TEXT:
            pass

        color = "#000000" if self.current_tool == TOOL_ERASER else self.current_color
        self.current_stroke = Stroke(
            tool=self.current_tool,
            color=color,
            line_width=line_width,
            opacity=opacity,
            font_size=self.current_font_size,
        )
        self.current_stroke.points.append(point)

        if self.current_tool == TOOL_ERASER:
            self._erase_at_point(point)

    def continue_stroke(self, point):
        if self.current_tool == TOOL_SCREENSHOT:
            if self.screenshot_region:
                self.screenshot_region = (self.screenshot_region[0], point)
            return

        if self.current_stroke:
            self.current_stroke.points.append(point)
            if self.current_stroke.tool == TOOL_ERASER:
                self._erase_at_point(point)

    def end_stroke(self):
        if self.current_tool == TOOL_SCREENSHOT:
            return

        if self.current_stroke:
            if self.current_stroke.tool == TOOL_FADING_INK:
                self.current_stroke.created_at = time.time()
            if self.current_stroke.tool == TOOL_TEXT:
                if len(self.current_stroke.points) >= 1:
                    self.strokes.append(self.current_stroke)
                    self.undone_strokes.clear()
            elif len(self.current_stroke.points) >= 2:
                if self.current_stroke.tool == TOOL_ERASER:
                    pass  # Already erased in real-time
                else:
                    self.strokes.append(self.current_stroke)
                self.undone_strokes.clear()
        self.current_stroke = None

    def add_text_stroke(self, text, position):
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
        if not self.current_stroke:
            return
        eraser_radius = self.current_stroke.line_width / 2.0
        self.strokes = [
            s for s in self.strokes
            if not self._stroke_hit_test(s, point, eraser_radius)
        ]

    @staticmethod
    def _stroke_hit_test(stroke, point, eraser_radius):
        threshold = eraser_radius + stroke.line_width / 2.0
        threshold_sq = threshold * threshold
        px, py = point
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

    def prune_faded(self):
        now = time.time()
        self.strokes = [
            s for s in self.strokes
            if s.tool != TOOL_FADING_INK or s.created_at is None
            or (now - s.created_at) < FADING_INK_DURATION
        ]


# ============================================================
# Helper: Color manipulation
# ============================================================

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def color_with_alpha_hex(hex_color, alpha):
    """Blend hex_color with white at the given alpha for simulated transparency on opaque canvas."""
    r, g, b = hex_to_rgb(hex_color)
    bg = 255  # white background for blending
    r2 = int(r * alpha + bg * (1 - alpha))
    g2 = int(g * alpha + bg * (1 - alpha))
    b2 = int(b * alpha + bg * (1 - alpha))
    return rgb_to_hex(r2, g2, b2)

def stipple_for_alpha(alpha):
    """Return a tkinter stipple pattern name for approximate transparency."""
    if alpha >= 0.75:
        return ""
    elif alpha >= 0.5:
        return "gray75"
    elif alpha >= 0.25:
        return "gray50"
    else:
        return "gray25"


# ============================================================
# Overlay Canvas Window
# ============================================================

class OverlayWindow:
    """Full-screen transparent overlay for drawing."""

    def __init__(self, app):
        self.app = app
        self.root = tk.Tk()
        self.root.title("ScreenDraw")
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 1.0)
        self.root.configure(bg='#010101')  # Near-black for transparency key
        self.root.overrideredirect(True)

        # Make window transparent using Windows API
        self.root.update_idletasks()
        self.hwnd = ctypes.windll.user32.GetForegroundWindow()

        # DPI awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height,
            bg='#010101',
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill='both', expand=True)

        # State
        self.is_drawing_enabled = True
        self.engine = DrawingEngine()

        # Cursor highlight
        self.cursor_highlight_enabled = False
        self.cursor_highlight_radius = 30.0
        self.cursor_highlight_shape = CURSOR_SHAPE_CIRCLE
        self._cursor_pos = None

        # Spotlight
        self.spotlight_enabled = False
        self.spotlight_radius = SPOTLIGHT_RADIUS_DEFAULT

        # Zoom
        self.zoom_enabled = False
        self.zoom_factor = ZOOM_FACTOR_DEFAULT

        # Laser pointer
        self.laser_pointer_enabled = False

        # Click animations
        self.click_animations_enabled = False
        self._click_anims = []
        self._anim_timer_id = None

        # Fading ink timer
        self._fade_timer_id = None

        # Text input
        self._text_entry = None
        self._text_input_point = None

        # Board mode background
        self._board_rect_id = None

        # Bind events
        self.canvas.bind('<ButtonPress-1>', self._on_mouse_down)
        self.canvas.bind('<B1-Motion>', self._on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_mouse_up)
        self.canvas.bind('<ButtonPress-3>', self._on_right_click)
        self.canvas.bind('<Motion>', self._on_mouse_move)

        # Setup window transparency
        self.root.after(50, self._setup_transparency)

    def _setup_transparency(self):
        """Set up layered window with color key transparency."""
        hwnd = self._get_hwnd()
        if hwnd:
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            # Set color key: #010101 becomes transparent
            user32.SetLayeredWindowAttributes(hwnd, 0x00010101, 255, LWA_COLORKEY)
            # Keep topmost
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                               SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        self.hwnd = hwnd

    def _get_hwnd(self):
        """Get the HWND for the tkinter root window."""
        return ctypes.windll.user32.FindWindowW(None, "ScreenDraw")

    def set_click_through(self, enabled):
        """Toggle click-through mode (WS_EX_TRANSPARENT)."""
        hwnd = self.hwnd or self._get_hwnd()
        if not hwnd:
            return
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enabled:
            style |= WS_EX_TRANSPARENT
            self.canvas.config(cursor="arrow")
        else:
            style &= ~WS_EX_TRANSPARENT
            self.canvas.config(cursor="crosshair")
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    # ---- Drawing ----

    def redraw(self):
        """Clear and redraw all strokes and overlays."""
        self.canvas.delete("all")

        # Board mode background
        if self.engine.board_mode == BOARD_WHITE:
            self.canvas.create_rectangle(0, 0, self.screen_width, self.screen_height,
                                         fill='white', outline='')
        elif self.engine.board_mode == BOARD_BLACK:
            self.canvas.create_rectangle(0, 0, self.screen_width, self.screen_height,
                                         fill='black', outline='')

        # Prune faded strokes
        self.engine.prune_faded()

        now = time.time()

        # Draw all strokes
        for stroke in self.engine.strokes:
            self._draw_stroke(stroke, now)
        if self.engine.current_stroke:
            self._draw_stroke(self.engine.current_stroke, now)

        # Spotlight overlay
        if self.spotlight_enabled and self._cursor_pos:
            self._draw_spotlight()

        # Zoom lens
        if self.zoom_enabled and self._cursor_pos:
            self._draw_zoom_lens()

        # Cursor highlight
        if self.cursor_highlight_enabled and self._cursor_pos:
            self._draw_cursor_highlight()

        # Laser pointer
        if self.laser_pointer_enabled and self._cursor_pos:
            self._draw_laser_pointer()

        # Click animations
        if self._click_anims:
            self._draw_click_anims()

        # Screenshot selection
        if self.engine.screenshot_region:
            self._draw_screenshot_selection()

    def _draw_stroke(self, stroke, now=None):
        if stroke.tool == TOOL_TEXT:
            self._draw_text_stroke(stroke)
            return

        if len(stroke.points) < 2:
            return

        # Calculate opacity for fading ink
        opacity = stroke.opacity
        if stroke.tool == TOOL_FADING_INK and stroke.created_at is not None and now is not None:
            elapsed = now - stroke.created_at
            fade = max(0.0, 1.0 - elapsed / FADING_INK_DURATION)
            opacity = fade
            if opacity <= 0:
                return

        if stroke.tool == TOOL_ERASER:
            return

        color = stroke.color
        stipple = stipple_for_alpha(opacity) if opacity < 0.75 else ""
        width = stroke.line_width

        if stroke.tool in (TOOL_PEN, TOOL_HIGHLIGHTER, TOOL_FADING_INK):
            # Smooth freehand stroke
            if len(stroke.points) >= 2:
                coords = []
                for p in stroke.points:
                    coords.extend([p[0], p[1]])
                self.canvas.create_line(
                    *coords,
                    fill=color,
                    width=width,
                    capstyle='round',
                    joinstyle='round',
                    smooth=True,
                    stipple=stipple,
                )

        elif stroke.tool == TOOL_LINE:
            start = stroke.points[0]
            end = stroke.points[-1]
            self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=color, width=width, capstyle='round',
                stipple=stipple,
            )

        elif stroke.tool == TOOL_ARROW:
            start = stroke.points[0]
            end = stroke.points[-1]
            # Line
            self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=color, width=width, capstyle='round',
                stipple=stipple,
            )
            # Arrowhead
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            head_length = max(15.0, width * 5)
            head_angle = math.pi / 6
            p1x = end[0] - head_length * math.cos(angle - head_angle)
            p1y = end[1] - head_length * math.sin(angle - head_angle)
            p2x = end[0] - head_length * math.cos(angle + head_angle)
            p2y = end[1] - head_length * math.sin(angle + head_angle)
            self.canvas.create_polygon(
                end[0], end[1], p1x, p1y, p2x, p2y,
                fill=color, outline=color, stipple=stipple,
            )

        elif stroke.tool == TOOL_RECTANGLE:
            start = stroke.points[0]
            end = stroke.points[-1]
            self.canvas.create_rectangle(
                start[0], start[1], end[0], end[1],
                outline=color, width=width, stipple=stipple,
            )

        elif stroke.tool == TOOL_CIRCLE:
            start = stroke.points[0]
            end = stroke.points[-1]
            self.canvas.create_oval(
                start[0], start[1], end[0], end[1],
                outline=color, width=width, stipple=stipple,
            )

    def _draw_text_stroke(self, stroke):
        if not stroke.text_content or not stroke.points:
            return
        pt = stroke.points[0]
        self.canvas.create_text(
            pt[0], pt[1],
            text=stroke.text_content,
            fill=stroke.color,
            font=("Segoe UI", int(stroke.font_size)),
            anchor='w',
        )

    def _draw_cursor_highlight(self):
        cx, cy = self._cursor_pos
        r = self.cursor_highlight_radius
        shape = self.cursor_highlight_shape

        if shape == CURSOR_SHAPE_SQUIRCLE:
            # Rounded rectangle approximation
            offset = r * 0.35
            self.canvas.create_rectangle(
                cx - r, cy - r, cx + r, cy + r,
                outline=self.engine.current_color,
                width=2,
                stipple="gray50",
            )
        elif shape == CURSOR_SHAPE_RING:
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=self.engine.current_color,
                width=3,
            )
        else:  # CURSOR_SHAPE_CIRCLE
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=self.engine.current_color,
                width=2,
                stipple="gray50",
            )

    def _draw_spotlight(self):
        cx, cy = self._cursor_pos
        sr = self.spotlight_radius
        # Draw 4 dark rectangles around the spotlight circle
        # Top
        self.canvas.create_rectangle(0, 0, self.screen_width, max(0, cy - sr),
                                     fill='gray10', stipple='gray75', outline='')
        # Bottom
        self.canvas.create_rectangle(0, min(self.screen_height, cy + sr),
                                     self.screen_width, self.screen_height,
                                     fill='gray10', stipple='gray75', outline='')
        # Left
        self.canvas.create_rectangle(0, max(0, cy - sr), max(0, cx - sr),
                                     min(self.screen_height, cy + sr),
                                     fill='gray10', stipple='gray75', outline='')
        # Right
        self.canvas.create_rectangle(min(self.screen_width, cx + sr), max(0, cy - sr),
                                     self.screen_width, min(self.screen_height, cy + sr),
                                     fill='gray10', stipple='gray75', outline='')
        # Circular cutout border
        self.canvas.create_oval(
            cx - sr, cy - sr, cx + sr, cy + sr,
            outline='white', width=2,
        )

    def _draw_zoom_lens(self):
        cx, cy = self._cursor_pos
        zr = ZOOM_LENS_RADIUS
        zf = self.zoom_factor

        # Draw a bordered circle for the zoom lens
        self.canvas.create_oval(
            cx - zr, cy - zr, cx + zr, cy + zr,
            outline='white', width=2.5,
            fill='#020202',  # slightly different from transparent key
        )

        # Redraw strokes scaled inside the lens area
        # For each stroke, draw a zoomed version clipped to the lens
        for stroke in self.engine.strokes:
            if stroke.tool == TOOL_TEXT or stroke.tool == TOOL_ERASER:
                continue
            if len(stroke.points) < 2:
                continue
            # Scale points relative to cursor
            zoomed_points = []
            for p in stroke.points:
                zx = cx + (p[0] - cx) * zf
                zy = cy + (p[1] - cy) * zf
                # Only include if within lens
                if (zx - cx) ** 2 + (zy - cy) ** 2 <= zr * zr:
                    zoomed_points.append((zx, zy))

            if len(zoomed_points) >= 2:
                coords = []
                for p in zoomed_points:
                    coords.extend([p[0], p[1]])
                if stroke.tool in (TOOL_PEN, TOOL_HIGHLIGHTER, TOOL_FADING_INK):
                    self.canvas.create_line(
                        *coords, fill=stroke.color,
                        width=stroke.line_width * zf,
                        capstyle='round', joinstyle='round', smooth=True,
                    )
                elif stroke.tool == TOOL_LINE:
                    self.canvas.create_line(
                        coords[0], coords[1], coords[-2], coords[-1],
                        fill=stroke.color, width=stroke.line_width * zf,
                    )

    def _draw_laser_pointer(self):
        cx, cy = self._cursor_pos
        lr = LASER_POINTER_RADIUS
        # Glow
        self.canvas.create_oval(
            cx - lr * 2.5, cy - lr * 2.5, cx + lr * 2.5, cy + lr * 2.5,
            fill='#FF3333', outline='', stipple='gray50',
        )
        # Core dot
        self.canvas.create_oval(
            cx - lr, cy - lr, cx + lr, cy + lr,
            fill='red', outline='',
        )

    def _draw_click_anims(self):
        now = time.time()
        remaining = []
        for (pt, start_time, is_right) in self._click_anims:
            elapsed = now - start_time
            if elapsed >= CLICK_ANIM_DURATION:
                continue
            progress = elapsed / CLICK_ANIM_DURATION
            radius = CLICK_ANIM_MAX_RADIUS * progress
            color = '#007AFF' if is_right else self.engine.current_color
            self.canvas.create_oval(
                pt[0] - radius, pt[1] - radius,
                pt[0] + radius, pt[1] + radius,
                outline=color, width=2,
            )
            remaining.append((pt, start_time, is_right))
        self._click_anims = remaining

    def _draw_screenshot_selection(self):
        start, end = self.engine.screenshot_region
        x1, y1 = start
        x2, y2 = end
        if abs(x2 - x1) > 1 and abs(y2 - y1) > 1:
            self.canvas.create_rectangle(
                0, 0, self.screen_width, self.screen_height,
                fill='black', stipple='gray25', outline='',
            )
            self.canvas.create_rectangle(
                min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2),
                outline='white', width=2, dash=(6, 4),
            )

    # ---- Mouse Events ----

    def _on_mouse_down(self, event):
        # Click animation
        if self.click_animations_enabled:
            self._click_anims.append(((event.x, event.y), time.time(), False))
            self._start_anim_timer()

        if not self.is_drawing_enabled:
            return

        point = (event.x, event.y)

        if self.engine.current_tool == TOOL_TEXT:
            self._show_text_input(point)
            return

        self.engine.begin_stroke(point)
        self.redraw()

    def _on_mouse_drag(self, event):
        if not self.is_drawing_enabled:
            return
        point = (event.x, event.y)
        self._cursor_pos = point
        self.engine.continue_stroke(point)
        self.redraw()

    def _on_mouse_up(self, event):
        if not self.is_drawing_enabled:
            return

        if self.engine.current_tool == TOOL_SCREENSHOT:
            if self.engine.screenshot_region:
                self._take_screenshot()
            self.engine.screenshot_region = None
            self.redraw()
            return

        was_fading = (self.engine.current_stroke and
                      self.engine.current_stroke.tool == TOOL_FADING_INK)
        self.engine.end_stroke()
        if was_fading:
            self._start_fade_timer()
        self.redraw()

    def _on_right_click(self, event):
        if self.click_animations_enabled:
            self._click_anims.append(((event.x, event.y), time.time(), True))
            self._start_anim_timer()

    def _on_mouse_move(self, event):
        needs_track = (self.cursor_highlight_enabled or self.spotlight_enabled
                       or self.zoom_enabled or self.laser_pointer_enabled)
        if needs_track:
            self._cursor_pos = (event.x, event.y)
            self.redraw()

    # ---- Text Input ----

    def _show_text_input(self, point):
        if self._text_entry:
            self._cancel_text_input()

        self._text_input_point = point
        self._text_entry = tk.Entry(
            self.canvas,
            font=("Segoe UI", int(self.engine.current_font_size)),
            fg=self.engine.current_color,
            bg='white',
            insertbackground=self.engine.current_color,
            bd=1,
            relief='solid',
            width=30,
        )
        self.canvas.create_window(point[0], point[1], window=self._text_entry, anchor='w',
                                  tags='text_input')
        self._text_entry.focus_set()
        self._text_entry.bind('<Return>', lambda e: self._commit_text_input())
        self._text_entry.bind('<Escape>', lambda e: self._cancel_text_input())

    def _commit_text_input(self):
        if not self._text_entry:
            return
        text = self._text_entry.get()
        if text and self._text_input_point:
            self.engine.add_text_stroke(text, self._text_input_point)
        self._text_entry.destroy()
        self._text_entry = None
        self._text_input_point = None
        self.canvas.delete('text_input')
        self.redraw()

    def _cancel_text_input(self):
        if self._text_entry:
            self._text_entry.destroy()
            self._text_entry = None
            self._text_input_point = None
            self.canvas.delete('text_input')

    # ---- Timers ----

    def _start_fade_timer(self):
        if self._fade_timer_id is not None:
            return

        def tick():
            has_fading = any(
                s.tool == TOOL_FADING_INK and s.created_at is not None
                for s in self.engine.strokes
            )
            if has_fading:
                self.redraw()
                self._fade_timer_id = self.root.after(50, tick)
            else:
                self._fade_timer_id = None
                self.redraw()

        self._fade_timer_id = self.root.after(50, tick)

    def _start_anim_timer(self):
        if self._anim_timer_id is not None:
            return

        def tick():
            now = time.time()
            self._click_anims = [
                a for a in self._click_anims if (now - a[1]) < CLICK_ANIM_DURATION
            ]
            if self._click_anims:
                self.redraw()
                self._anim_timer_id = self.root.after(20, tick)
            else:
                self._anim_timer_id = None
                self.redraw()

        self._anim_timer_id = self.root.after(20, tick)

    # ---- Screenshot ----

    def _take_screenshot(self):
        """Capture the selected region using Windows API."""
        if not self.engine.screenshot_region:
            return
        start, end = self.engine.screenshot_region
        x1 = int(min(start[0], end[0]))
        y1 = int(min(start[1], end[1]))
        x2 = int(max(start[0], end[0]))
        y2 = int(max(start[1], end[1]))
        w = x2 - x1
        h = y2 - y1
        if w < 5 or h < 5:
            return

        # Temporarily hide for clean capture
        self.root.withdraw()
        self.root.update()
        time.sleep(0.2)

        try:
            import pyautogui
            screenshot = pyautogui.screenshot(region=(x1, y1, w, h))
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filepath = os.path.join(desktop, f"ScreenDraw_{timestamp}.png")
            screenshot.save(filepath)
            # Also copy to clipboard
            try:
                import io
                from PIL import Image
                output = io.BytesIO()
                screenshot.convert("RGB").save(output, "BMP")
                data = output.getvalue()[14:]  # strip BMP header
                output.close()
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
            except ImportError:
                pass
            print(f"ScreenDraw: Screenshot saved to {filepath}")
        except ImportError:
            print("ScreenDraw: pyautogui not available for screenshots")
        except Exception as e:
            print(f"ScreenDraw: Screenshot error: {e}")
        finally:
            self.root.deiconify()
            self.root.update()

    def run(self):
        self.root.mainloop()


# ============================================================
# Toolbar Panel
# ============================================================

class ToolbarPanel:
    def __init__(self, app, overlay):
        self.app = app
        self.overlay = overlay

        self.win = tk.Toplevel(overlay.root)
        self.win.title("ScreenDraw Toolbar")
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        self.win.attributes('-alpha', 0.92)

        self.panel_width = 52
        screen_height = overlay.screen_height

        # Position on right side
        x = overlay.screen_width - self.panel_width - 16
        total_height = min(screen_height - 80, 1100)
        y = (screen_height - total_height) // 2
        self.win.geometry(f"{self.panel_width}x{total_height}+{x}+{y}")

        # Dark background
        self.win.configure(bg='#2D2D2D')

        # Scrollable frame
        self.container = tk.Frame(self.win, bg='#2D2D2D')
        self.container.pack(fill='both', expand=True)

        # Scrollable canvas for many buttons
        self.scroll_canvas = tk.Canvas(self.container, bg='#2D2D2D',
                                       highlightthickness=0, width=self.panel_width)
        self.scrollbar = tk.Scrollbar(self.container, orient='vertical',
                                       command=self.scroll_canvas.yview)
        self.btn_frame = tk.Frame(self.scroll_canvas, bg='#2D2D2D')

        self.btn_frame.bind('<Configure>',
                           lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
        self.scroll_canvas.create_window((0, 0), window=self.btn_frame, anchor='nw')
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_canvas.pack(side='left', fill='both', expand=True)
        # Don't show scrollbar to keep it clean; use mousewheel
        self.scroll_canvas.bind_all('<MouseWheel>',
                                    lambda e: self.scroll_canvas.yview_scroll(-1 * (e.delta // 120), 'units'))

        # Button references
        self._tool_buttons = []
        self._color_buttons = []
        self._drawing_toggle_btn = None
        self._whiteboard_btn = None
        self._blackboard_btn = None
        self._cursor_highlight_btn = None
        self._cursor_shape_btn = None
        self._spotlight_btn = None
        self._zoom_btn = None
        self._laser_btn = None
        self._click_anim_btn = None
        self._record_btn = None

        self._selected_tool_index = 0
        self._selected_color_index = 0

        self._build_ui()

        # Make toolbar draggable
        self._drag_data = {'x': 0, 'y': 0}
        self.win.bind('<ButtonPress-1>', self._on_drag_start)
        self.win.bind('<B1-Motion>', self._on_drag_motion)

    def _on_drag_start(self, event):
        self._drag_data['x'] = event.x
        self._drag_data['y'] = event.y

    def _on_drag_motion(self, event):
        x = self.win.winfo_x() + event.x - self._drag_data['x']
        y = self.win.winfo_y() + event.y - self._drag_data['y']
        self.win.geometry(f"+{x}+{y}")

    def _build_ui(self):
        frame = self.btn_frame
        btn_size = 36

        def add_label(text):
            lbl = tk.Label(frame, text=text, fg='#999999', bg='#2D2D2D',
                          font=('Segoe UI', 7), anchor='center')
            lbl.pack(fill='x', pady=(4, 0))

        def add_separator():
            sep = tk.Frame(frame, bg='#555555', height=1)
            sep.pack(fill='x', padx=6, pady=3)

        def add_button(text, command, tooltip="", bg_color='#3A3A3A', fg_color='white', width=btn_size):
            btn = tk.Button(
                frame, text=text, command=command,
                bg=bg_color, fg=fg_color,
                activebackground='#555555', activeforeground='white',
                bd=0, relief='flat',
                font=('Segoe UI', 9),
                width=3, height=1,
                cursor='hand2',
            )
            btn.pack(fill='x', padx=4, pady=1)
            if tooltip:
                self._bind_tooltip(btn, tooltip)
            return btn

        # Drawing toggle
        self._drawing_toggle_btn = add_button(
            "✏️", self.app.toggle_drawing, "Toggle Drawing (D)",
            bg_color='#2D5F2D', fg_color='#90EE90',
        )

        add_separator()
        add_label("Tools")

        # Tool buttons with symbols
        tool_symbols = {
            TOOL_PEN: "🖊",
            TOOL_HIGHLIGHTER: "🖍",
            TOOL_LINE: "╱",
            TOOL_ARROW: "↗",
            TOOL_RECTANGLE: "▭",
            TOOL_CIRCLE: "○",
            TOOL_TEXT: "T",
            TOOL_ERASER: "⌫",
            TOOL_FADING_INK: "✨",
        }

        for i, tool in enumerate(ALL_TOOLS):
            shortcut = TOOL_SHORTCUTS.get(tool, "")
            tooltip = f"{TOOL_LABELS[tool]} ({shortcut})" if shortcut else TOOL_LABELS[tool]
            btn = add_button(
                tool_symbols.get(tool, "?"),
                lambda t=tool, idx=i: self.app.set_tool(t, idx),
                tooltip,
            )
            self._tool_buttons.append(btn)

        self._update_tool_selection()

        add_separator()

        # Screenshot
        add_button("📷", self.app.activate_screenshot_mode, "Screenshot (S)")

        add_separator()
        add_label("Color")

        # Color buttons in a grid
        color_frame = tk.Frame(frame, bg='#2D2D2D')
        color_frame.pack(fill='x', padx=4, pady=2)

        for i, (color, name) in enumerate(COLORS):
            row = i // 2
            col = i % 2
            btn = tk.Button(
                color_frame, text="", bg=color,
                activebackground=color,
                bd=1, relief='solid',
                width=2, height=1,
                cursor='hand2',
                command=lambda c=color, idx=i: self.app.set_color(c, idx),
            )
            btn.grid(row=row, column=col, padx=1, pady=1, sticky='ew')
            self._color_buttons.append(btn)
            self._bind_tooltip(btn, name)

        color_frame.columnconfigure(0, weight=1)
        color_frame.columnconfigure(1, weight=1)

        self._update_color_selection()

        add_separator()
        add_label("Size")

        # Size slider
        self._size_slider = tk.Scale(
            frame, from_=1, to=20, orient='horizontal',
            command=lambda v: self.app.set_line_width(float(v)),
            bg='#2D2D2D', fg='white', troughcolor='#555555',
            highlightthickness=0, bd=0, sliderrelief='flat',
            length=40,
        )
        self._size_slider.set(3)
        self._size_slider.pack(fill='x', padx=4, pady=2)

        add_separator()
        add_label("Board")

        self._whiteboard_btn = add_button("⬜", self.app.toggle_whiteboard, "Whiteboard (W)")
        self._blackboard_btn = add_button("⬛", self.app.toggle_blackboard, "Blackboard (B)")

        self._cursor_highlight_btn = add_button("◎", self.app.toggle_cursor_highlight, "Cursor Highlight (H)",
                                                bg_color='#3A3A3A', fg_color='#FFD700')
        self._cursor_shape_btn = add_button("◌", self.app.cycle_cursor_shape, "Cursor Shape (Shift+H)",
                                            bg_color='#3A3A3A', fg_color='#FFD700')

        self._spotlight_btn = add_button("💡", self.app.toggle_spotlight, "Spotlight (F)",
                                         bg_color='#3A3A3A', fg_color='#FF9500')
        self._zoom_btn = add_button("🔍", self.app.toggle_zoom, "Zoom Lens (Z)",
                                     bg_color='#3A3A3A', fg_color='#5856D6')
        self._laser_btn = add_button("🔴", self.app.toggle_laser, "Laser Pointer (L)",
                                      bg_color='#3A3A3A', fg_color='#FF3B30')
        self._click_anim_btn = add_button("⊙", self.app.toggle_click_anims, "Click Animations (K)",
                                           bg_color='#3A3A3A', fg_color='#FF2D55')

        add_separator()

        # Action buttons
        add_button("↩", self.app.undo, "Undo (Ctrl+Z)")
        add_button("↪", self.app.redo, "Redo (Ctrl+Shift+Z)")
        add_button("🗑", self.app.clear_all, "Clear All (C)", fg_color='#FF3B30')

        add_separator()

        self._record_btn = add_button("⏺", self.app.toggle_recording, "Record Screen (R)",
                                       fg_color='#FF3B30')

        add_separator()

        add_button("─", self.app.minimize_app, "Minimize (M)", fg_color='#FF9500')
        add_button("✕", self.app.quit_app, "Quit (Esc)", fg_color='#8E8E93')

    def _bind_tooltip(self, widget, text):
        """Simple tooltip on hover."""
        tip_win = [None]

        def show(event):
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{event.x_root - 120}+{event.y_root - 5}")
            tw.attributes('-topmost', True)
            lbl = tk.Label(tw, text=text, bg='#333333', fg='white',
                          font=('Segoe UI', 9), padx=6, pady=2, relief='solid', bd=1)
            lbl.pack()
            tip_win[0] = tw

        def hide(event):
            if tip_win[0]:
                tip_win[0].destroy()
                tip_win[0] = None

        widget.bind('<Enter>', show)
        widget.bind('<Leave>', hide)

    def _update_tool_selection(self):
        for i, btn in enumerate(self._tool_buttons):
            if i == self._selected_tool_index:
                btn.configure(bg='#4A6FA5')
            else:
                btn.configure(bg='#3A3A3A')

    def _update_color_selection(self):
        for i, btn in enumerate(self._color_buttons):
            if i == self._selected_color_index:
                btn.configure(relief='solid', bd=3)
            else:
                btn.configure(relief='solid', bd=1)

    def update_drawing_toggle(self, is_enabled):
        if self._drawing_toggle_btn:
            if is_enabled:
                self._drawing_toggle_btn.configure(bg='#2D5F2D', fg='#90EE90')
            else:
                self._drawing_toggle_btn.configure(bg='#5F2D2D', fg='#999999')

    def update_board_buttons(self, mode):
        if self._whiteboard_btn:
            self._whiteboard_btn.configure(
                bg='#4A6FA5' if mode == BOARD_WHITE else '#3A3A3A')
        if self._blackboard_btn:
            self._blackboard_btn.configure(
                bg='#4A6FA5' if mode == BOARD_BLACK else '#3A3A3A')

    def update_cursor_highlight_button(self, is_enabled):
        if self._cursor_highlight_btn:
            self._cursor_highlight_btn.configure(
                bg='#5F5F2D' if is_enabled else '#3A3A3A')

    def update_spotlight_button(self, is_enabled):
        if self._spotlight_btn:
            self._spotlight_btn.configure(
                bg='#5F3A2D' if is_enabled else '#3A3A3A')

    def update_zoom_button(self, is_enabled):
        if self._zoom_btn:
            self._zoom_btn.configure(
                bg='#3A3A5F' if is_enabled else '#3A3A3A')

    def update_laser_button(self, is_enabled):
        if self._laser_btn:
            self._laser_btn.configure(
                bg='#5F2D2D' if is_enabled else '#3A3A3A')

    def update_click_anim_button(self, is_enabled):
        if self._click_anim_btn:
            self._click_anim_btn.configure(
                bg='#5F2D3A' if is_enabled else '#3A3A3A')

    def update_record_button(self, is_recording):
        if self._record_btn:
            self._record_btn.configure(
                bg='#5F2D2D' if is_recording else '#3A3A3A')

    def select_tool(self, index):
        self._selected_tool_index = index
        self._update_tool_selection()

    def select_color(self, index):
        self._selected_color_index = index
        self._update_color_selection()

    def show(self):
        self.win.deiconify()

    def hide(self):
        self.win.withdraw()


# ============================================================
# System Tray Icon
# ============================================================

class SystemTray:
    """System tray icon using pystray."""

    def __init__(self, app):
        self.app = app
        self._icon = None
        self._thread = None

    def start(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            # Create a simple icon
            img = Image.new('RGB', (64, 64), '#007AFF')
            draw = ImageDraw.Draw(img)
            draw.ellipse([8, 8, 56, 56], fill='white')
            draw.text((22, 18), "SD", fill='#007AFF')

            menu = pystray.Menu(
                pystray.MenuItem("Toggle Drawing (D)", lambda: self.app.root_after(self.app.toggle_drawing)),
                pystray.MenuItem("Show/Hide (M)", lambda: self.app.root_after(self.app.toggle_visibility)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", lambda: self.app.root_after(self.app.quit_app)),
            )

            self._icon = pystray.Icon("ScreenDraw", img, "ScreenDraw", menu)
            self._thread = threading.Thread(target=self._icon.run, daemon=True)
            self._thread.start()
        except ImportError:
            print("ScreenDraw: pystray not available, no system tray icon")

    def stop(self):
        if self._icon:
            self._icon.stop()


# ============================================================
# Screen Recorder
# ============================================================

class ScreenRecorder:
    """Screen recording using opencv-python if available."""

    def __init__(self):
        self.is_recording = False
        self._thread = None
        self._stop_event = threading.Event()
        self.recording_path = None

    def start(self, screen_width, screen_height):
        if self.is_recording:
            return False
        try:
            import cv2
            import numpy as np
        except ImportError:
            print("ScreenDraw: opencv-python and numpy required for recording. pip install opencv-python numpy")
            return False

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(desktop, f"ScreenDraw_Recording_{timestamp}.avi")
        self.recording_path = filepath

        self._stop_event.clear()
        self.is_recording = True

        def record_loop():
            try:
                import cv2
                import numpy as np
                import pyautogui

                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                out = cv2.VideoWriter(filepath, fourcc, 15.0, (screen_width, screen_height))

                while not self._stop_event.is_set():
                    img = pyautogui.screenshot()
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    out.write(frame)
                    time.sleep(1.0 / 15.0)

                out.release()
                print(f"ScreenDraw: Recording saved to {filepath}")
            except Exception as e:
                print(f"ScreenDraw: Recording error: {e}")
            finally:
                self.is_recording = False

        self._thread = threading.Thread(target=record_loop, daemon=True)
        self._thread.start()
        print(f"ScreenDraw: Recording started -> {filepath}")
        return True

    def stop(self):
        if not self.is_recording:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        self.is_recording = False


# ============================================================
# App Controller
# ============================================================

class ScreenDrawApp:
    def __init__(self):
        self.overlay = None
        self.toolbar = None
        self.tray = None
        self.recorder = ScreenRecorder()
        self._hotkey_thread = None
        self._running = True

    def run(self):
        self.overlay = OverlayWindow(self)

        # Build toolbar after overlay
        self.overlay.root.after(100, self._setup_after_init)
        self.overlay.run()

    def _setup_after_init(self):
        self.toolbar = ToolbarPanel(self, self.overlay)
        self.tray = SystemTray(self)
        self.tray.start()
        self._setup_hotkeys()

    def root_after(self, func):
        """Schedule a function to run on the main thread."""
        try:
            self.overlay.root.after(0, func)
        except Exception:
            pass

    def _setup_hotkeys(self):
        """Set up global keyboard shortcuts."""
        try:
            import keyboard

            keyboard.add_hotkey('d', lambda: self.root_after(self.toggle_drawing))
            keyboard.add_hotkey('1', lambda: self.root_after(lambda: self.set_tool(TOOL_PEN, 0)))
            keyboard.add_hotkey('2', lambda: self.root_after(lambda: self.set_tool(TOOL_HIGHLIGHTER, 1)))
            keyboard.add_hotkey('3', lambda: self.root_after(lambda: self.set_tool(TOOL_LINE, 2)))
            keyboard.add_hotkey('4', lambda: self.root_after(lambda: self.set_tool(TOOL_ARROW, 3)))
            keyboard.add_hotkey('5', lambda: self.root_after(lambda: self.set_tool(TOOL_RECTANGLE, 4)))
            keyboard.add_hotkey('6', lambda: self.root_after(lambda: self.set_tool(TOOL_CIRCLE, 5)))
            keyboard.add_hotkey('7', lambda: self.root_after(lambda: self.set_tool(TOOL_TEXT, 6)))
            keyboard.add_hotkey('8', lambda: self.root_after(lambda: self.set_tool(TOOL_ERASER, 7)))
            keyboard.add_hotkey('9', lambda: self.root_after(lambda: self.set_tool(TOOL_FADING_INK, 8)))
            keyboard.add_hotkey('s', lambda: self.root_after(self.activate_screenshot_mode))
            keyboard.add_hotkey('w', lambda: self.root_after(self.toggle_whiteboard))
            keyboard.add_hotkey('b', lambda: self.root_after(self.toggle_blackboard))
            keyboard.add_hotkey('h', lambda: self.root_after(self.toggle_cursor_highlight))
            keyboard.add_hotkey('shift+h', lambda: self.root_after(self.cycle_cursor_shape))
            keyboard.add_hotkey('f', lambda: self.root_after(self.toggle_spotlight))
            keyboard.add_hotkey('z', lambda: self.root_after(self.toggle_zoom))
            keyboard.add_hotkey('l', lambda: self.root_after(self.toggle_laser))
            keyboard.add_hotkey('k', lambda: self.root_after(self.toggle_click_anims))
            keyboard.add_hotkey('r', lambda: self.root_after(self.toggle_recording))
            keyboard.add_hotkey('m', lambda: self.root_after(self.minimize_app))
            keyboard.add_hotkey('c', lambda: self.root_after(self.clear_all))
            keyboard.add_hotkey('ctrl+z', lambda: self.root_after(self.undo))
            keyboard.add_hotkey('ctrl+shift+z', lambda: self.root_after(self.redo))
            keyboard.add_hotkey('ctrl+q', lambda: self.root_after(self.quit_app))
            keyboard.add_hotkey('escape', lambda: self.root_after(self.quit_app))
            keyboard.add_hotkey('[', lambda: self.root_after(self._decrease_size))
            keyboard.add_hotkey(']', lambda: self.root_after(self._increase_size))

            print("ScreenDraw: Global hotkeys registered")
        except ImportError:
            print("ScreenDraw: 'keyboard' package not available. pip install keyboard")
            print("ScreenDraw: Hotkeys disabled; use the toolbar instead.")

    # ---- Tool / Color / Size ----

    def set_tool(self, tool, index):
        self.overlay.engine.current_tool = tool
        if self.toolbar:
            self.toolbar.select_tool(index)

    def set_color(self, color, index):
        self.overlay.engine.current_color = color
        if self.toolbar:
            self.toolbar.select_color(index)

    def set_line_width(self, width):
        self.overlay.engine.current_line_width = width

    def _decrease_size(self):
        w = max(1, self.overlay.engine.current_line_width - 1)
        self.overlay.engine.current_line_width = w

    def _increase_size(self):
        w = min(30, self.overlay.engine.current_line_width + 1)
        self.overlay.engine.current_line_width = w

    # ---- Drawing State ----

    def toggle_drawing(self):
        ov = self.overlay
        ov.is_drawing_enabled = not ov.is_drawing_enabled
        ov.set_click_through(not ov.is_drawing_enabled)
        if self.toolbar:
            self.toolbar.update_drawing_toggle(ov.is_drawing_enabled)

    # ---- Undo / Redo / Clear ----

    def undo(self):
        self.overlay.engine.undo()
        self.overlay.redraw()

    def redo(self):
        self.overlay.engine.redo()
        self.overlay.redraw()

    def clear_all(self):
        self.overlay.engine.clear_all()
        self.overlay.redraw()

    # ---- Board Modes ----

    def toggle_whiteboard(self):
        engine = self.overlay.engine
        engine.board_mode = BOARD_NONE if engine.board_mode == BOARD_WHITE else BOARD_WHITE
        self.overlay.redraw()
        if self.toolbar:
            self.toolbar.update_board_buttons(engine.board_mode)

    def toggle_blackboard(self):
        engine = self.overlay.engine
        engine.board_mode = BOARD_NONE if engine.board_mode == BOARD_BLACK else BOARD_BLACK
        self.overlay.redraw()
        if self.toolbar:
            self.toolbar.update_board_buttons(engine.board_mode)

    # ---- Cursor Highlight ----

    def toggle_cursor_highlight(self):
        ov = self.overlay
        ov.cursor_highlight_enabled = not ov.cursor_highlight_enabled
        if not ov.cursor_highlight_enabled:
            ov.redraw()
        if self.toolbar:
            self.toolbar.update_cursor_highlight_button(ov.cursor_highlight_enabled)

    def cycle_cursor_shape(self):
        ov = self.overlay
        current = ov.cursor_highlight_shape
        idx = CURSOR_SHAPES.index(current) if current in CURSOR_SHAPES else 0
        new_idx = (idx + 1) % len(CURSOR_SHAPES)
        ov.cursor_highlight_shape = CURSOR_SHAPES[new_idx]
        if ov.cursor_highlight_enabled:
            ov.redraw()

    # ---- Spotlight ----

    def toggle_spotlight(self):
        ov = self.overlay
        ov.spotlight_enabled = not ov.spotlight_enabled
        if not ov.spotlight_enabled:
            ov.redraw()
        if self.toolbar:
            self.toolbar.update_spotlight_button(ov.spotlight_enabled)

    # ---- Zoom ----

    def toggle_zoom(self):
        ov = self.overlay
        ov.zoom_enabled = not ov.zoom_enabled
        if not ov.zoom_enabled:
            ov.redraw()
        if self.toolbar:
            self.toolbar.update_zoom_button(ov.zoom_enabled)

    # ---- Laser Pointer ----

    def toggle_laser(self):
        ov = self.overlay
        ov.laser_pointer_enabled = not ov.laser_pointer_enabled
        if not ov.laser_pointer_enabled:
            ov.redraw()
        if self.toolbar:
            self.toolbar.update_laser_button(ov.laser_pointer_enabled)

    # ---- Click Animations ----

    def toggle_click_anims(self):
        ov = self.overlay
        ov.click_animations_enabled = not ov.click_animations_enabled
        if self.toolbar:
            self.toolbar.update_click_anim_button(ov.click_animations_enabled)

    # ---- Screenshot ----

    def activate_screenshot_mode(self):
        self.overlay.engine.current_tool = TOOL_SCREENSHOT
        if self.toolbar:
            self.toolbar.select_tool(-1)

    # ---- Recording ----

    def toggle_recording(self):
        if self.recorder.is_recording:
            self.recorder.stop()
            if self.toolbar:
                self.toolbar.update_record_button(False)
        else:
            success = self.recorder.start(
                self.overlay.screen_width, self.overlay.screen_height)
            if self.toolbar:
                self.toolbar.update_record_button(success)

    # ---- Minimize / Restore ----

    def minimize_app(self):
        self.overlay.root.withdraw()
        if self.toolbar:
            self.toolbar.hide()

    def toggle_visibility(self):
        if self.overlay.root.state() == 'withdrawn':
            self.restore_app()
        else:
            self.minimize_app()

    def restore_app(self):
        self.overlay.root.deiconify()
        self.overlay.root.attributes('-topmost', True)
        if self.toolbar:
            self.toolbar.show()

    # ---- Quit ----

    def quit_app(self):
        self._running = False
        if self.recorder.is_recording:
            self.recorder.stop()
        if self.tray:
            self.tray.stop()
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            self.overlay.root.destroy()
        except Exception:
            pass
        sys.exit(0)


# ============================================================
# Main
# ============================================================

def main():
    # Enable DPI awareness
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    app = ScreenDrawApp()
    app.run()


if __name__ == "__main__":
    main()
