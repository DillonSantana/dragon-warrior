"""AppKit drawing for the on-screen emblem. macOS only; must run on the main thread."""

import time
from pathlib import Path

import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSCompositingOperationSourceOver,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGraphicsContext,
    NSImage,
    NSLineBreakByWordWrapping,
    NSMakeRect,
    NSMutableParagraphStyle,
    NSPanel,
    NSParagraphStyleAttributeName,
    NSScreen,
    NSShadow,
    NSStatusWindowLevel,
    NSString,
    NSTextAlignmentCenter,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
    NSZeroRect,
)

from rollout.app import overlay
from rollout.state import AssistantState

EMBLEM_SIZE = 150
CAPTION_HEIGHT = 90


def _color(rgb, alpha=1.0):
    r, g, b = rgb
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, alpha)


class EmblemView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(EmblemView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.status = "awake"
        self.caption = ""
        self.image = None
        self.started = time.monotonic()
        return self

    def isOpaque(self):
        return False

    def drawRect_(self, rect):
        t = time.monotonic() - self.started
        bounds = self.bounds()
        width, height = bounds.size.width, bounds.size.height

        # Dark rounded card so the caption reads on any wallpaper
        _color((0, 0, 0), 0.55).setFill()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bounds, 28, 28).fill()

        size = EMBLEM_SIZE
        ex = (width - size) / 2
        ey = height - size - 30
        strength = overlay.glow(self.status, t)

        # Ring around the emblem: a spinning arc while thinking, a full ring otherwise
        center = (ex + size / 2, ey + size / 2)
        ring = NSBezierPath.bezierPath()
        if self.status == "thinking":
            start = overlay.spinner_angle(t)
            ring.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_(
                center, size / 2 + 12, start, start + 100
            )
        else:
            ring.appendBezierPathWithOvalInRect_(NSMakeRect(ex - 12, ey - 12, size + 24, size + 24))
        ring.setLineWidth_(4)
        _color(overlay.GLOW_COLOR, strength).setStroke()
        ring.stroke()

        NSGraphicsContext.saveGraphicsState()
        shadow = NSShadow.alloc().init()
        shadow.setShadowColor_(_color(overlay.GLOW_COLOR, strength))
        shadow.setShadowBlurRadius_(10 + 25 * strength)
        shadow.setShadowOffset_((0, 0))
        shadow.set()
        if self.image is not None:
            self.image.drawInRect_fromRect_operation_fraction_(
                NSMakeRect(ex, ey, size, size), NSZeroRect, NSCompositingOperationSourceOver, 1.0
            )
        else:
            for i, (rgb, points) in enumerate(overlay.emblem_shapes()):
                if i == 1:
                    NSShadow.alloc().init().set()  # glow only around the shield
                path = NSBezierPath.bezierPath()
                for j, (x, y) in enumerate(points):
                    point = (ex + x * size, ey + y * size)
                    if j == 0:
                        path.moveToPoint_(point)
                    else:
                        path.lineToPoint_(point)
                path.closePath()
                _color(rgb).setFill()
                path.fill()
        NSGraphicsContext.restoreGraphicsState()

        if self.caption:
            style = NSMutableParagraphStyle.alloc().init()
            style.setAlignment_(NSTextAlignmentCenter)
            style.setLineBreakMode_(NSLineBreakByWordWrapping)
            attributes = {
                NSFontAttributeName: NSFont.systemFontOfSize_(15),
                NSForegroundColorAttributeName: NSColor.whiteColor(),
                NSParagraphStyleAttributeName: style,
            }
            NSString.stringWithString_(self.caption).drawInRect_withAttributes_(
                NSMakeRect(20, 10, width - 40, CAPTION_HEIGHT), attributes
            )


class Overlay:
    """A click-through floating window that fades in when RollOut is awake."""

    def __init__(self, position: str = "bottom", image: Path | None = None):
        width, height = overlay.SIZE
        frame = NSScreen.mainScreen().visibleFrame()
        x, y = overlay.window_origin(
            (frame.origin.x, frame.origin.y, frame.size.width, frame.size.height), position
        )
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, width, height),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setHasShadow_(False)
        self.panel.setLevel_(NSStatusWindowLevel)
        self.panel.setIgnoresMouseEvents_(True)
        self.panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        self.view = EmblemView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        if image is not None and image.is_file():
            self.view.image = NSImage.alloc().initWithContentsOfFile_(str(image))
        self.panel.setContentView_(self.view)
        self.panel.setAlphaValue_(0.0)
        self.alpha = 0.0
        self.last_tick = time.monotonic()

    def tick(self, state: AssistantState) -> None:
        """Call from a main-thread timer about 30 times a second."""
        now = time.monotonic()
        dt, self.last_tick = now - self.last_tick, now
        target = overlay.target_alpha(state.status, state.paused.is_set())
        if target == 0.0 and self.alpha == 0.0:
            return
        if target > 0 and self.alpha == 0.0:
            self.panel.orderFrontRegardless()
        self.alpha = overlay.step_alpha(self.alpha, target, dt)
        self.panel.setAlphaValue_(self.alpha)
        if target > 0:
            # Keep the last caption on screen while fading out
            self.view.status = state.status
            self.view.caption = overlay.caption_for(state.caption)
        self.view.setNeedsDisplay_(True)
        if self.alpha == 0.0:
            self.panel.orderOut_(None)
