"""Arrow Pad's right/middle-click toggles (ClickSwap) on a private Xvfb display: a receiver
window records which buttons arrive. Skipped where Xvfb isn't installed."""
import ctypes as C
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("Xvfb"), "needs Xvfb")
class ClickSwapTest(unittest.TestCase):
    def test_toggles(self):
        # Xvfb picks a free display and says which (-displayfd) once it's ready: no fixed number
        # that could collide, no guessing how long it takes to start.
        r, w = os.pipe()
        xvfb = subprocess.Popen(["Xvfb", "-displayfd", str(w), "-screen", "0", "640x480x24", "-nolisten", "tcp"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, pass_fds=(w,))
        os.close(w)
        self.addCleanup(lambda: (xvfb.terminate(), xvfb.wait(10)))
        with os.fdopen(r) as f:
            number = f.readline().strip()
        if not number.isdigit():
            self.skipTest("Xvfb didn't start")
        display = ":" + number
        env = mock.patch.dict(os.environ, {"ARROWPAD_CLICK_DISPLAY": display,
                                           "QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("DISPLAY", None)
        argv = mock.patch.object(sys, "argv", ["arrowpad.py"])   # no target: needs no running session
        argv.start()
        self.addCleanup(argv.stop)
        sys.path.insert(0, str(ROOT / "packs/original/arrowpad"))
        self.addCleanup(lambda: sys.path.remove(str(ROOT / "packs/original/arrowpad")))
        spec = importlib.util.spec_from_file_location("ap", ROOT / "packs/original/arrowpad" / "arrowpad.py")
        ap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ap)
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        logs = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, logs, True)
        ap.ClickSwap.LOG = Path(logs) / "clicks.log"
        D = display.encode()
        x = C.CDLL("libX11.so.6"); t = C.CDLL("libXtst.so.6")
        x.XOpenDisplay.restype = C.c_void_p
        for f, a in [("XDefaultRootWindow", [C.c_void_p]), ("XFlush", [C.c_void_p]), ("XPending", [C.c_void_p]),
                     ("XMapWindow", [C.c_void_p, C.c_ulong]), ("XSelectInput", [C.c_void_p, C.c_ulong, C.c_long]),
                     ("XNextEvent", [C.c_void_p, C.c_void_p]), ("XSync", [C.c_void_p, C.c_int])]:
            getattr(x, f).argtypes = a
        x.XDefaultRootWindow.restype = C.c_ulong
        x.XCreateSimpleWindow.restype = C.c_ulong
        x.XCreateSimpleWindow.argtypes = [C.c_void_p, C.c_ulong] + [C.c_int] * 4 + [C.c_uint, C.c_ulong, C.c_ulong]
        t.XTestFakeButtonEvent.argtypes = [C.c_void_p, C.c_uint, C.c_int, C.c_ulong]
        t.XTestFakeMotionEvent.argtypes = [C.c_void_p, C.c_int, C.c_int, C.c_int, C.c_ulong]
        rx = x.XOpenDisplay(D)
        win = x.XCreateSimpleWindow(rx, x.XDefaultRootWindow(rx), 0, 0, 640, 480, 0, 0, 0)
        x.XSelectInput(rx, win, (1 << 2) | (1 << 3)); x.XMapWindow(rx, win); x.XSync(rx, 0)
        inj = x.XOpenDisplay(D)

        def pump(sec):
            end = time.monotonic() + sec
            while time.monotonic() < end:
                app.processEvents(); time.sleep(0.01)

        def received():
            got = []; ev = (C.c_long * 24)()
            while x.XPending(rx):
                x.XNextEvent(rx, ev); ints = C.cast(ev, C.POINTER(C.c_int))
                if ints[0] == 4:
                    got.append(ints[21])
            return got

        def click(b, release=True):
            t.XTestFakeMotionEvent(inj, -1, 100, 100, 0); t.XTestFakeButtonEvent(inj, b, 1, 0)
            if release:
                t.XTestFakeButtonEvent(inj, b, 0, 0)
            x.XFlush(inj)

        def check(name, cond):
            self.assertTrue(cond, name)

        received()
        cs = ap.ClickSwap(lambda: None)
        received()
        cs.arm("RMB"); pump(0.2); click(1); pump(0.3)
        check("left click while RMB armed arrives as button 3, toggle off after", received() == [3] and cs.armed is None)
        cs.arm("MMB"); pump(0.2); click(4); pump(0.3)
        check("scroll while armed passes through as button 4, still armed", received() == [4] and cs.armed == "MMB")
        click(1); pump(0.3)
        check("then a click arrives as button 2", received() == [2] and cs.armed is None)
        cs.arm("RMB"); pump(0.2); click(1, release=False); pump(2.0)
        check("press without release is replayed after 1.5 s", received() == [3] and cs.armed is None)
        t.XTestFakeButtonEvent(inj, 1, 0, 0); x.XFlush(inj); pump(0.2); received()
        cs.TIMEOUT = 1; cs.arm("RMB"); pump(1.4)
        check("timeout cancels; later clicks are untouched", cs.armed is None)
        click(1); pump(0.3)
        check("left click after cancel arrives as button 1", received() == [1])
        cs.TIMEOUT = 10; cs.arm("MMB"); pump(0.1); cs.disarm("dashboard closed"); click(1); pump(0.3)
        check("disarm (dashboard closed) releases the pointer", received() == [1])
        cs.arm("RMB"); cs.arm("RMB"); click(1); pump(0.3)
        check("tapping R twice toggles it off", received() == [1] and cs.armed is None)


if __name__ == "__main__":
    unittest.main()
