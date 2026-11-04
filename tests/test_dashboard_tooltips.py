"""vr-dashboard's lib.js tip(): the icon buttons' tooltips in the SteamVR dashboard, run in Node
with a fake clock and a fake React tree (a button in a PANEL placed by an XFORM, in a mount).

A title: shows nothing in the headset (Chromium draws it in a popup window, never in the panels),
so tip() draws the text as a panel of its own, timed as the desktop window's tooltips
(lib/tooltips.py): 700 ms on the button, the laser's wobble not starting the wait again, gone on
leaving or pressing, shown for twice Qt's time. What only the headset shows: that the panel is
drawn, where it is, and that the laser's events arrive as pointer events."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "packs/core/vr-dashboard/lib.js"

HARNESS = r"""
let now = 0, timers = [], nextId = 1;
globalThis.setTimeout = (fn, ms) => { const id = nextId++; timers.push({ id, at: now + ms, fn }); return id; };
globalThis.clearTimeout = (id) => { timers = timers.filter((t) => t.id !== id); };
globalThis.setInterval = () => 0;
globalThis.clearInterval = () => {};
const advance = (to) => {
  for (;;) {
    timers.sort((a, b) => a.at - b.at || a.id - b.id);
    const t = timers[0];
    if (!t || t.at > to) break;
    timers.shift(); now = t.at; t.fn();
  }
  now = to;
};
globalThis.window = globalThis;
const S = JSON.parse(process.argv[1]);

// The dashboard's tree: container > Holder (a mount) > XFORM > PANEL > the panel's top div > buttons.
function PANEL() {} function XFORM() {} function Holder() {}
Holder.sftMount = { key: 'm', side: 'right' };
const FK = '__reactFiber$test';
const fiber = (type, props, stateNode, parent) => {
  const f = { type, memoizedProps: props, stateNode, return: parent, child: null, sibling: null };
  if (parent) { f.sibling = parent.child; parent.child = f; }
  if (stateNode) stateNode[FK] = f;
  return f;
};
const dom = (rect, title) => ({ isConnected: true, title, getBoundingClientRect: () => rect,
                                getAttribute(n) { return n === 'title' ? this.title : null; } });
const container = fiber(null, null, null, null);
const holder = fiber(Holder, {}, null, container);
const xform = fiber(XFORM, { parent_id: 'anchor-L', translation: { x: -0.2, y: 0.1, z: -0.03 }, ...S.xform }, null, holder);
const topProps = { style: {} };
const panel = fiber(PANEL, { width: 0.34, origin: 4, debug_name: 'Test', interactive: true, children: { props: topProps },
                             ...S.panel }, null, xform);
const top = dom({ left: 1000, top: 500, width: 340, height: 680 });
const topFiber = fiber('div', topProps, top, panel);
const buttons = {};
for (const [name, text, left] of [['a', 'Close', 1300], ['b', 'Volume up', 1100]]) {
  buttons[name] = dom({ left, top: 510, width: 20, height: 20 }, text);
  buttons[name].tip = S.long && name === 'a' ? 'x'.repeat(150) : text;
  if (S.long && name === 'a') buttons[name].title = buttons[name].tip;
  fiber('div', {}, buttons[name], topFiber);
}
buttons.loose = dom({ left: 0, top: 0, width: 10, height: 10 }, 'Nowhere');     // (in no panel)
buttons.loose.tip = 'Nowhere';
globalThis.document = { getElementById: () => ({ '__reactContainer$test': container }) };
if (!S.noFrame) {
  globalThis.FrameStore = { frames: [{ activePage: { GetPanelAnchorID: (a) => (a === 3 ? 'anchor-L' : `other-${a}`),
                                                      size: { latestMeasuredPanelLocalHeight: 2, latestMeasuredPanelWorldHeight: 1 } } }] };
}
eval(require('fs').readFileSync(S.lib, 'utf8'));
const L = window.__sftLib;

const label = (piece) => piece.props.children.props.children.props.children;     // wrapper > XFORM > PANEL > div
const out = [];
for (const [ms, what, name] of S.steps) {
  advance(ms);
  const b = buttons[name];
  if (what === 'enter') L.tip(b.tip).onPointerEnter({ currentTarget: b });
  else if (what === 'leave') L.tip(b.tip).onPointerLeave({ currentTarget: b });
  else if (what === 'down') L.tip(b.tip).onPointerDown({ currentTarget: b });
  else if (what === 'detach') b.isConnected = false;
  else if (what === 'retitle') b.title = 'Open the settings';
  else if (what === 'check') {
    const piece = L.tipFor('m'), st = L.tipState();
    if (!piece) { out.push(null); continue; }
    const x = piece.props.children, p = x.props.children, d = p.props.children;
    out.push({ text: d.props.children, opacity: d.props.style.opacity, parent: x.props.parent_id,
               at: x.props.translation, width: p.props.width, origin: p.props.origin, interactive: p.props.interactive,
               curve: p.props.curvature_origin_id ?? null, edge: piece.props.style.right, other: L.tipFor('n'),
               state: st.shown && st.shown.text });
  }
}
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "needs Node.js to run lib.js")
class Tooltips(unittest.TestCase):
    def run_js(self, steps, **opts):
        """steps: [ms, what, button]; for each 'check', the tooltip piece drawn then (or None)."""
        arg = json.dumps({"lib": str(LIB), "steps": steps, "xform": {}, "panel": {}, **opts})
        r = subprocess.run(["node", "-e", HARNESS, arg], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def shown(self, steps, **opts):
        """For each check: the text shown, or None."""
        return [c and c["text"] for c in self.run_js(steps, **opts)]

    def test_shows_after_700_ms_on_the_button(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [699, "check", "a"], [700, "check", "a"]]), [None, "Close"])

    def test_first_drawn_see_through_then_shown(self):
        c = self.run_js([[0, "enter", "a"], [700, "check", "a"], [819, "check", "a"], [820, "check", "a"]])
        self.assertEqual([x["opacity"] for x in c], [0, 0, 1])
        self.assertEqual(c[2]["state"], "Close")

    def test_placed_just_above_the_button_and_in_front(self):
        """Panel 0.34 wide (340 px: 1 mm a px) centred at (-0.2, 0.1), the window's units 2 to the
        metre: the button's top 10 px below the panel's (0.44), its middle 310 px from the left."""
        c = self.run_js([[0, "enter", "a"], [800, "check", "a"]])[0]
        self.assertEqual(c["parent"], "anchor-L")
        self.assertAlmostEqual(c["at"]["x"], -0.37 + 0.310)
        self.assertAlmostEqual(c["at"]["y"], 0.44 - 0.010 + 0.006 * 2)          # GAP_M, in the window's units
        self.assertAlmostEqual(c["at"]["z"], 0.004 * 2)                         # in front of the plane, not set back
        self.assertEqual((c["origin"], c["interactive"], c["edge"], c["other"]), (7, False, "0px", None))
        text_px = min(560, -(-len("Close") * 20 * 0.55 // 1) + 2 * 10 + 8)      # (Node has no canvas: the estimate)
        self.assertAlmostEqual(c["width"], text_px * 0.0005 * 2)

    def test_the_panels_origin_and_curve_are_followed(self):
        """A panel hung by its top centre, curved: the tooltip bends with it."""
        c = self.run_js([[0, "enter", "a"], [800, "check", "a"]],
                        xform={"translation": {"x": 0, "y": 0, "z": 0.002}}, panel={"origin": 1, "curvature_origin_id": "curve-1"})[0]
        self.assertAlmostEqual(c["at"]["x"], -0.17 + 0.310)
        self.assertAlmostEqual(c["at"]["y"], 0 - 0.010 + 0.012)
        self.assertAlmostEqual(c["at"]["z"], 0.002 + 0.008)
        self.assertEqual(c["curve"], "curve-1")

    def test_without_the_window_its_size_comes_from_the_panel(self):
        c = self.run_js([[0, "enter", "a"], [800, "check", "a"]], noFrame=True)[0]
        self.assertAlmostEqual(c["at"]["z"], 0.004 * (0.001 / 0.0012))

    def test_a_wobble_off_the_edge_and_back_does_not_start_the_wait_again(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [300, "leave", "a"], [400, "enter", "a"], [700, "check", "a"]]),
                         ["Close"])

    def test_leaving_for_longer_starts_it_again(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [300, "leave", "a"], [500, "enter", "a"],
                                     [700, "check", "a"], [1199, "check", "a"], [1200, "check", "a"]]), [None, None, "Close"])

    def test_gone_on_leaving(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [800, "check", "a"], [900, "leave", "a"],
                                     [1049, "check", "a"], [1050, "check", "a"]]), ["Close", "Close", None])

    def test_gone_on_a_press_and_back_only_after_leaving(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [800, "check", "a"], [900, "down", "a"], [900, "check", "a"],
                                     [5000, "check", "a"], [5100, "leave", "a"], [5300, "enter", "a"],
                                     [5999, "check", "a"], [6000, "check", "a"]]), ["Close", None, None, None, "Close"])

    def test_a_press_during_the_wait_stops_it(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [300, "down", "a"], [2000, "check", "a"]]), [None])

    def test_shown_twice_as_long_as_qt(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [20699, "check", "a"], [20700, "check", "a"]]), ["Close", None])
        # 150 characters: Qt's 10 s and 40 ms for each past 100, twice
        self.assertEqual(self.shown([[0, "enter", "a"], [24699, "check", "a"], [24700, "check", "a"]], long=True),
                         ["x" * 150, None])

    def test_moving_to_another_button_waits_for_that_one(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [500, "leave", "a"], [500, "enter", "b"],
                                     [700, "check", "b"], [1199, "check", "b"], [1200, "check", "b"]]),
                         [None, None, "Volume up"])

    def test_the_text_as_the_button_says_it_now(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [300, "retitle", "a"], [700, "check", "a"]]), ["Open the settings"])

    def test_a_button_gone_from_the_page_gets_none(self):
        self.assertEqual(self.shown([[0, "enter", "a"], [300, "detach", "a"], [700, "check", "a"]]), [None])
        self.assertEqual(self.shown([[0, "enter", "a"], [800, "detach", "a"], [800, "check", "a"]]), [None])

    def test_a_button_in_none_of_our_panels_gets_none(self):
        self.assertEqual(self.shown([[0, "enter", "loose"], [800, "check", "loose"]]), [None])


if __name__ == "__main__":
    unittest.main()
