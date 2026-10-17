"""Live capture of a single window using ScreenCaptureKit."""
import objc
import Quartz
from CoreMedia import CMSampleBufferGetImageBuffer, CMTimeMake
from Foundation import NSObject
from ScreenCaptureKit import SCContentFilter, SCStream, SCStreamConfiguration

try:
    from ScreenCaptureKit import SCStreamOutputTypeScreen
except ImportError:
    SCStreamOutputTypeScreen = 0

try:
    from libdispatch import dispatch_queue_create
    _QUEUE = dispatch_queue_create(b"eveview.capture", None)
except ImportError:
    _QUEUE = None  # ScreenCaptureKit falls back to a default queue

_PIXEL_FORMAT_BGRA = 1111970369  # FourCC 'BGRA'
_CI_CONTEXT = Quartz.CIContext.contextWithOptions_(None)


class _StreamHandler(
    NSObject,
    protocols=[objc.protocolNamed("SCStreamOutput"), objc.protocolNamed("SCStreamDelegate")],
):
    """Receives frames and stop events from an ``SCStream``.

    Python attributes ``on_frame(cg_image)`` and ``on_stop(error)`` are set by
    :class:`WindowCapture`. Both are called from the capture queue, not the
    main thread.
    """

    def stream_didOutputSampleBuffer_ofType_(self, stream, sample_buffer, output_type):
        if output_type != SCStreamOutputTypeScreen:
            return
        on_frame = getattr(self, "on_frame", None)
        if on_frame is None:
            return
        try:
            with objc.autorelease_pool():
                pixel_buffer = CMSampleBufferGetImageBuffer(sample_buffer)
                if pixel_buffer is None:  # idle frame: window content unchanged
                    return
                image = Quartz.CIImage.imageWithCVPixelBuffer_(pixel_buffer)
                cg_image = _CI_CONTEXT.createCGImage_fromRect_(image, image.extent())
                if cg_image is not None:
                    on_frame(cg_image)
        except Exception as e:
            print(f"[capture] Frame error: {e}")

    def stream_didStopWithError_(self, stream, error):
        on_stop = getattr(self, "on_stop", None)
        if on_stop is not None:
            on_stop(error)


def _make_config(width, height, fps):
    """Build an ``SCStreamConfiguration`` for the given output size and frame rate."""
    cfg = SCStreamConfiguration.alloc().init()
    cfg.setWidth_(int(width))
    cfg.setHeight_(int(height))
    cfg.setMinimumFrameInterval_(CMTimeMake(1, int(fps)))
    cfg.setPixelFormat_(_PIXEL_FORMAT_BGRA)
    cfg.setShowsCursor_(False)
    cfg.setQueueDepth_(3)
    if cfg.respondsToSelector_("setIgnoreShadowsSingleWindow:"):
        cfg.setIgnoreShadowsSingleWindow_(True)
    return cfg


def _log_error(what):
    """Return a completion handler that logs ``error`` if one is reported."""
    def handler(error):
        if error is not None:
            print(f"[capture] {what}: {error}")
    return handler


class WindowCapture:
    """A running capture stream for one window.

    :param sc_window: the ``SCWindow`` to capture.
    :param width: output width in pixels.
    :param height: output height in pixels.
    :param fps: maximum frames per second.
    :param on_frame: ``callable(cg_image)``, called from the capture queue.
    :param on_stop: ``callable(error)``, called if the stream stops by itself
        (for example because the window was closed).
    :raises RuntimeError: if the stream output cannot be attached.
    """

    def __init__(self, sc_window, width, height, fps, on_frame, on_stop):
        self._settings = (width, height, fps)
        self._handler = _StreamHandler.alloc().init()
        self._handler.on_frame = on_frame
        self._handler.on_stop = on_stop

        content_filter = SCContentFilter.alloc().initWithDesktopIndependentWindow_(sc_window)
        self._stream = SCStream.alloc().initWithFilter_configuration_delegate_(
            content_filter, _make_config(width, height, fps), self._handler
        )
        ok, error = self._stream.addStreamOutput_type_sampleHandlerQueue_error_(
            self._handler, SCStreamOutputTypeScreen, _QUEUE, None
        )
        if not ok:
            raise RuntimeError(f"addStreamOutput failed: {error}")
        self._stream.startCaptureWithCompletionHandler_(_log_error("Start capture"))

    def update(self, width, height, fps):
        """Change output size and frame rate. No-op if nothing changed."""
        if (width, height, fps) == self._settings:
            return
        self._settings = (width, height, fps)
        self._stream.updateConfiguration_completionHandler_(
            _make_config(width, height, fps), _log_error("Update capture")
        )

    def stop(self):
        """Stop the stream and detach the callbacks."""
        self._handler.on_frame = None
        self._handler.on_stop = None
        self._stream.stopCaptureWithCompletionHandler_(_log_error("Stop capture"))