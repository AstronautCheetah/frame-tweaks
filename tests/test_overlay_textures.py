"""vrkit.Textures: an overlay's picture as an OpenGL texture, refilled in place. Every file
SetOverlayFromFile loads stays in vrcompositor's memory until SteamVR restarts (51 MB for 20
pictures, measured on a Frame), and Arrow Pad loaded a new file at each redraw. OpenGL and
SteamVR are stand-ins."""
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vrkit  # noqa: E402
from helpers import load_script  # noqa: E402


def fake_vr():
    return types.SimpleNamespace(Texture_t=types.SimpleNamespace, VRTextureBounds_t=types.SimpleNamespace,
                                 TextureType_OpenGL=1, ColorSpace_Auto=0)


class Overlays:
    """IVROverlay, noting the calls Textures makes."""
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def setOverlayTexture(self, overlay, texture):
        if self.fail:
            raise RuntimeError("VROverlayError_RequestFailed")
        self.calls.append(("texture", overlay, texture.handle, texture.eType))

    def setOverlayTextureBounds(self, overlay, b):
        self.calls.append(("bounds", overlay, (b.uMin, b.vMin, b.uMax, b.vMax)))


class GL:
    made = 0

    def __init__(self):
        GL.made += 1
        self.next, self.uploads, self.deleted = 40, [], []

    def texture(self):
        self.next += 1
        return self.next

    def upload(self, tex, image, size):
        self.uploads.append((tex, size))
        return image.width(), image.height()

    def delete(self, tex):
        self.deleted.append(tex)


class Image:
    def __init__(self, w, h):
        self.w, self.h = w, h

    def width(self):
        return self.w

    def height(self):
        return self.h


class Textures(unittest.TestCase):
    def setUp(self):
        GL.made = 0
        p = mock.patch.object(vrkit, "_GL", GL)
        p.start()
        self.addCleanup(p.stop)

    def test_one_texture_per_overlay_refilled_in_place(self):
        t, ov = vrkit.Textures(fake_vr()), Overlays()
        self.assertTrue(t.set(ov, 7, Image(800, 600)))
        self.assertTrue(t.set(ov, 7, Image(800, 600)))
        self.assertTrue(t.set(ov, 9, Image(900, 100)))
        self.assertEqual(GL.made, 1)                                      # (one context for all)
        self.assertEqual(t.gl.uploads, [(41, None), (41, (800, 600)), (42, None)])
        # flipped once per overlay (GL's first row is the bottom one), then the texture each time
        self.assertEqual(ov.calls, [("bounds", 7, (0.0, 1.0, 1.0, 0.0)), ("texture", 7, 41, 1),
                                    ("texture", 7, 41, 1),
                                    ("bounds", 9, (0.0, 1.0, 1.0, 0.0)), ("texture", 9, 42, 1)])
        t.forget(7)
        self.assertEqual(t.gl.deleted, [41])
        self.assertTrue(t.set(ov, 7, Image(800, 600)))                    # (a new overlay of that number)
        self.assertEqual(t.gl.uploads[-1], (43, None))

    def test_a_failure_turns_them_off_for_good_and_unflips(self):
        logged = []
        t, ov = vrkit.Textures(fake_vr(), log=logged.append), Overlays()
        self.assertTrue(t.set(ov, 7, Image(8, 6)))
        ov.fail = True
        self.assertFalse(t.set(ov, 7, Image(8, 6)))
        self.assertEqual(ov.calls[-1], ("bounds", 7, (0.0, 0.0, 1.0, 1.0)))   # (a file's rows: the right way up)
        ov.fail, ov.calls = False, []
        self.assertFalse(t.set(ov, 9, Image(8, 6)))                       # (files from then on, every overlay)
        self.assertEqual(ov.calls, [])
        self.assertEqual(len(logged), 1)
        self.assertIn("files", logged[0])

    def test_no_opengl_means_files(self):
        def none():
            raise OSError("no surfaceless EGL display")
        with mock.patch.object(vrkit, "_GL", none):
            t, ov = vrkit.Textures(fake_vr()), Overlays()
            self.assertFalse(t.set(ov, 7, Image(8, 6)))
        self.assertEqual(ov.calls, [])


class ArrowPad(unittest.TestCase):
    """The pad's redraw with a texture to be had: no file goes to SteamVR, and nothing covers it."""

    def test_a_redraw_goes_as_a_texture(self):
        from PyQt6.QtGui import QColor, QImage
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        with mock.patch.dict(sys.modules, {"openvr": types.ModuleType("openvr")}):
            v = load_script(ROOT / "packs/core/arrowpad/vroverlay.py", "vroverlay_textures")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        o = v.OverlayHost.__new__(v.OverlayHost)
        img = QImage(300, 200, QImage.Format.Format_ARGB32)
        img.fill(QColor(10, 20, 30))
        calls = []
        o.pad = types.SimpleNamespace(grab=lambda: types.SimpleNamespace(toImage=lambda: img))
        o.ov = types.SimpleNamespace(setOverlayFromFile=lambda h, path: calls.append(("file", h)),
                                     showOverlay=lambda h: calls.append(("show", h)))
        o.textures = types.SimpleNamespace(set=lambda ov, h, image: calls.append(("texture", h)) or True)
        o.input_handle, o.cover, o.cover_path = 7, 8, None
        o.last_render, o.swapping, o.image_hash, o.tex_slot = 0.0, False, None, 0
        o.fit_size = lambda w, h: False
        o.set_input_size = lambda w, h: calls.append(("size", w, h))
        with mock.patch.object(v, "TEX_DIR", tmp.name):
            o.render()
            img.fill(QColor(200, 20, 30))
            o.last_render = 0.0
            o.render()
        self.assertEqual(calls, [("texture", 7), ("size", 300, 200)] * 2)
        # (the files stay for SteamVR's grab bar, which shows the latest: the last two kept, as before)
        self.assertEqual(len(list(Path(tmp.name).glob("arrowpad-overlay-*.png"))), 2)


if __name__ == "__main__":
    unittest.main()
