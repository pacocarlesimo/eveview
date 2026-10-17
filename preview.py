"""Preview windows: floating panels that show the live image of one EVE client."""
import threading

import AppKit
import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSCursor,
    NSEvent,
    NSFloatingWindowLevel,
    NSMakeRect,
    NSPanel,
    NSTrackingActiveAlways,
    NSTrackingArea,
    NSTrackingInVisibleRect,
    NSTrackingMouseEnteredAndExited,
    NSTrackingMouseMoved,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorIgnoresCycle,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from PyObjCTools import AppHelper
from Quartz import CALayer, CATextLayer, CATransaction, kCAGravityResizeAspect, kCATruncationEnd

import layout
MIN_WIDTH = 120
MAX_WIDTH = 1600
#: Distance from the border, in points, where dragging resizes instead of moving.
RESIZE_MARGIN = 8


def cg_color(hex_str, alpha=1.0):
    """Convert a ``#RRGGBB`` string to a ``CGColor``."""
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, alpha).CGColor()


def _rect(ns_rect):
    """Convert an ``NSRect`` to an ``(x, y, w, h)`` tuple."""
    return ns_rect.origin.x, ns_rect.origin.y, ns_rect.size.width, ns_rect.size.height


def _hit_edges(bounds, point):
    """Return the set of edges (``l``, ``r``, ``t``, ``b``) under ``point``."""
    w, h = bounds.size.width, bounds.size.height
    edges = set()
    if point.x <= RESIZE_MARGIN:
        edges.add("l")
    elif point.x >= w - RESIZE_MARGIN:
        edges.add("r")
    if point.y <= RESIZE_MARGIN:
        edges.add("b")
    elif point.y >= h - RESIZE_MARGIN:
        edges.add("t")
    return edges


_DIAGONALS = {
    frozenset("tl"): "NSCursorFrameResizePositionTopLeft",
    frozenset("tr"): "NSCursorFrameResizePositionTopRight",
    frozenset("bl"): "NSCursorFrameResizePositionBottomLeft",
    frozenset("br"): "NSCursorFrameResizePositionBottomRight",
}


def _cursor_for(edges):
    """Return the cursor matching the hovered edges.

    Diagonal resize cursors exist only on macOS 15+; older systems get a
    crosshair on corners.
    """
    if not edges:
        return NSCursor.arrowCursor()
    if len(edges) == 2 and NSCursor.respondsToSelector_("frameResizeCursorFromPosition:inDirections:"):
        position = getattr(AppKit, _DIAGONALS.get(frozenset(edges), ""), None)
        directions = getattr(AppKit, "NSCursorFrameResizeDirectionsAll", None)
        if position is not None and directions is not None:
            return NSCursor.frameResizeCursorFromPosition_inDirections_(position, directions)
    if edges <= {"l", "r"}:
        return NSCursor.resizeLeftRightCursor()
    if edges <= {"t", "b"}:
        return NSCursor.resizeUpDownCursor()
    return NSCursor.crosshairCursor()


class PreviewPanel(NSPanel):
    """Borderless panel that never takes keyboard focus away from EVE."""

    def canBecomeKeyWindow(self):
        return False

    def canBecomeMainWindow(self):
        return False


class PreviewView(NSView):
    """Content view of a preview: the image, the name label and mouse handling.

    Mouse events are forwarded to ``owner`` (a :class:`Preview`).
    """

    def initWithFrame_(self, frame):
        self = objc.super(PreviewView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.owner = None
        self.drag_start = None
        self.start_frame = None
        self.resize_edges = set()
        self.dragged = False

        self.setWantsLayer_(True)
        root = self.layer()
        if root is None:
            root = CALayer.layer()
            self.setLayer_(root)
        root.setBackgroundColor_(NSColor.blackColor().CGColor())
        root.setMasksToBounds_(True)

        image_layer = CALayer.layer()
        image_layer.setContentsGravity_(kCAGravityResizeAspect)
        root.addSublayer_(image_layer)

        label_layer = CATextLayer.layer()
        label_layer.setFont_("Helvetica-Bold")
        label_layer.setForegroundColor_(NSColor.whiteColor().CGColor())
        label_layer.setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.0, 0.55).CGColor())
        label_layer.setContentsScale_(2.0)
        label_layer.setTruncationMode_(kCATruncationEnd)
        root.addSublayer_(label_layer)

        self.image_layer = image_layer
        self.label_layer = label_layer

        tracking = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            ((0, 0), (0, 0)),
            NSTrackingMouseMoved | NSTrackingMouseEnteredAndExited
            | NSTrackingActiveAlways | NSTrackingInVisibleRect,
            self, None,
            )
        self.addTrackingArea_(tracking)
        return self

    def acceptsFirstMouse_(self, event):
        return True  # first click works immediately, without focusing the panel

    def setFrameSize_(self, size):
        objc.super(PreviewView, self).setFrameSize_(size)
        owner = getattr(self, "owner", None)
        if owner is not None:
            owner.layout()

    # --- cursor ---

    def mouseMoved_(self, event):
        owner = self.owner
        if owner is None or owner.locked:
            edges = set()
        else:
            point = self.convertPoint_fromView_(event.locationInWindow(), None)
            edges = _hit_edges(self.bounds(), point)
        _cursor_for(edges).set()

    def mouseExited_(self, event):
        NSCursor.arrowCursor().set()

    # --- click / move / resize ---

    def mouseDown_(self, event):
        owner = self.owner
        self.drag_start = NSEvent.mouseLocation()
        self.start_frame = _rect(self.window().frame())
        self.dragged = False
        if owner is None or owner.locked:
            self.resize_edges = set()
        else:
            point = self.convertPoint_fromView_(event.locationInWindow(), None)
            self.resize_edges = _hit_edges(self.bounds(), point)

    def mouseDragged_(self, event):
        owner = self.owner
        if owner is None or owner.locked or self.drag_start is None:
            return
        p = NSEvent.mouseLocation()
        dx = p.x - self.drag_start.x
        dy = p.y - self.drag_start.y
        if not self.dragged and abs(dx) < 3 and abs(dy) < 3:
            return  # ignore tiny movements so clicks stay clicks
        self.dragged = True
        owner.handle_drag(self.start_frame, self.resize_edges, dx, dy)

    def mouseUp_(self, event):
        self.drag_start = None
        owner = self.owner
        if owner is None:
            return
        if self.dragged:
            owner.handle_drag_end()
        else:
            owner.on_click()


class Preview:
    """A floating preview of one EVE client.

    :param name: label shown at the top-left.
    :param aspect: height / width ratio of the EVE window.
    :param x: initial x position (screen coordinates).
    :param y: initial y position (screen coordinates).
    :param width: initial width; height follows from ``aspect``.
    :param config: the :class:`config.Config` to read styling from.
    :param on_click: ``callable()`` invoked on a plain click.
    :param on_changed: ``callable()`` invoked after a move or resize.
    :param context: ``callable()`` returning ``(other_preview_rects, screen_rects)``
        for snapping.
    """

    def __init__(self, name, aspect, x, y, width, config, on_click, on_changed, context):
        self.aspect = aspect
        self.on_click = on_click
        self.on_changed = on_changed
        self.context = context
        self.closed = False
        self.visible = True
        self.locked = False
        self.snap_distance = 0
        self.font_size = config["name_font_size"]
        self.border_width = 0
        self.border_color = None
        self._frame_lock = threading.Lock()
        self._pending_frame = None
        self._flush_scheduled = False

        height = round(width * aspect)
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        panel = PreviewPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, width, height), style, NSBackingStoreBuffered, False
        )
        panel.setReleasedWhenClosed_(False)
        panel.setLevel_(NSFloatingWindowLevel)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorIgnoresCycle
        )
        panel.setHidesOnDeactivate_(False)
        panel.setFloatingPanel_(True)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setAcceptsMouseMovedEvents_(True)

        view = PreviewView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        panel.setContentView_(view)
        view.owner = self

        self.panel = panel
        self.view = view
        self.set_name(name)
        self.apply_style(config)
        panel.orderFrontRegardless()

    # --- appearance ---

    def layout(self):
        """Resize the image and label layers to the current view size."""
        bounds = self.view.bounds()
        w, h = bounds.size.width, bounds.size.height
        label_h = self.font_size + 8
        CATransaction.begin()
        CATransaction.setDisableActions_(True)
        self.view.image_layer.setFrame_(((0, 0), (w, h)))
        self.view.label_layer.setFrame_(((0, h - label_h), (w, label_h)))
        CATransaction.commit()

    def apply_style(self, config):
        """Apply every visual and behavioural option from ``config``."""
        self.font_size = config["name_font_size"]
        self.view.label_layer.setFontSize_(self.font_size)
        self.view.label_layer.setHidden_(not config["show_name"])
        self.border_width = config["active_border_width"] if config["highlight_active"] else 0
        self.border_color = cg_color(config["active_border_color"])
        self.locked = config["lock_positions"]
        self.snap_distance = config["snap_distance"] if config["snap_enabled"] else 0
        self.panel.setAlphaValue_(config["opacity"])
        self.layout()

    def set_name(self, name):
        """Set the label text."""
        self.view.label_layer.setString_(f" {name}")

    def submit_frame(self, surface):
        """Queue a new frame. Safe to call from any thread.

        Only the most recent frame is kept: if the main thread is busy,
        older frames are dropped instead of piling up in memory.
        """
        with self._frame_lock:
            self._pending_frame = surface
            if self._flush_scheduled:
                return
            self._flush_scheduled = True
        AppHelper.callAfter(self._flush_frame)

    def _flush_frame(self):
        with self._frame_lock:
            surface, self._pending_frame = self._pending_frame, None
            self._flush_scheduled = False
        if surface is None or self.closed:
            return
        CATransaction.begin()
        CATransaction.setDisableActions_(True)
        self.view.image_layer.setContents_(surface)
        CATransaction.commit()

    def set_active(self, active):
        """Draw or remove the active-client border."""
        root = self.view.layer()
        root.setBorderColor_(self.border_color)
        root.setBorderWidth_(self.border_width if active else 0)

    def set_visible(self, visible):
        """Show or hide the panel."""
        if visible == self.visible or self.closed:
            return
        self.visible = visible
        if visible:
            self.panel.orderFrontRegardless()
        else:
            self.panel.orderOut_(None)

    # --- geometry ---

    def rect(self):
        """Return the panel frame as ``(x, y, w, h)``."""
        return _rect(self.panel.frame())

    def frame(self):
        """Return ``(x, y, width)``, the values saved in the configuration."""
        x, y, w, _ = self.rect()
        return x, y, w

    def pixel_size(self, scale):
        """Return the capture size in pixels for the given backing scale factor."""
        b = self.view.bounds()
        return int(b.size.width * scale) // 2 * 2, int(b.size.height * scale) // 2 * 2

    def _set_rect(self, rect, animate=False):
        self.panel.setFrame_display_animate_(NSMakeRect(*rect), True, animate)

    def move_to(self, x, y, width):
        """Move and resize the panel; height follows the aspect ratio."""
        self._set_rect((x, y, width, round(width * self.aspect)))

    def handle_drag(self, start, edges, dx, dy):
        """Move (no ``edges``) or resize (with ``edges``) during a mouse drag."""
        others, screens = self.context()
        if edges:
            rect = layout.resize_rect(start, edges, dx, dy, self.aspect, others, screens,
                                      self.snap_distance, MIN_WIDTH, MAX_WIDTH)
        else:
            x, y, w, h = start
            rect = layout.snap_move((x + dx, y + dy, w, h), others, screens, self.snap_distance)
        self._set_rect(rect)

    def handle_drag_end(self):
        """Slide away from overlapping previews (if snapping is on) and notify."""
        if self.snap_distance > 0:
            others, _ = self.context()
            current = self.rect()
            fixed = layout.resolve_overlaps(current, others)
            if fixed != current:
                self._set_rect(fixed, animate=True)
        self.on_changed()

    def close(self):
        """Hide and release the panel. The preview cannot be reused afterwards."""
        self.closed = True
        self.view.owner = None
        self.panel.orderOut_(None)
        self.panel.close()