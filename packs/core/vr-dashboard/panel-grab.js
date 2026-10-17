// frame-tweaks panel-grab: SteamVR's own grab bar under each Frame Tweaks panel in VR (Arrow Pad,
// Screen snip's narration panel) while Steam's keyboard is open, to move it anywhere.
// While the keyboard shows, SteamVR hides where the controllers are from other programs (its
// keyboard privacy), so a panel can't follow the hand that grabs it: it only slides after the
// laser. SteamVR's dashboard still moves things: this puts the bar it draws under its own windows
// under the panel, in one of its grab transforms. Held, the panel hides and a picture of it
// follows the hand (SteamVR moves it, with the stick for nearer and further, as for its windows);
// let go, the panel is told where (by sft-dashboard: lib/vrkit.py DashboardGrab), and takes its
// picture's place. No controller pose leaves the dashboard: only where the panel was let go.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard, which installs it.
// requires: the grab bar | debug_name:"GrabHandle"
// requires: grabbing it | startMove(e){let t;switch(
// requires: what it moves | this.context.setState({parent_path:t})
// requires: grab transforms | "vsg-grab-transform"
// requires: the stick moving it | allow_scroll:!0,scroll_speed:8
// requires: asking where a node is | type:"transform_request"
// requires: the scene graph's requests | requestSGTransform(e){
// requires: the page's modules | webpackChunkvrwebui
// requires: Steam's keyboard showing | this.m_bKeyboardVisible=e.visible
(() => {
  const NAME = 'panel-grab', VERSION = 1;
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const L = window.__sftLib, DS = window.DashboardStore;
  if (!L || !DS) return 'not patched: dashboard pieces not found';
  // The bar's panel at scale 1, width 350: 0.333 m wide, 0.28 as tall as wide, its origin its
  // bottom centre, the bar across its middle (its picture is 470 x 132 px).
  const BAR_PX = 350, BAR_M = 0.66675 * BAR_PX / 700, BAR_TALL = 132 / 470, GAP_M = 0.005;
  const LAND_MS = 1500;                // the picture stays where it was let go until the panel is there

  // The dashboard's grab bar (GrabHandle: startMove/endMove, in a grab transform's context) and
  // grab transform (props target_mode, min_distance), as it renders them under its own bar.
  let BAR = null, GRAB = null;
  const types = () => {
    if (!(BAR && GRAB)) {
      L.walk((fb) => {
        const t = fb.type, p = fb.memoizedProps;
        if (typeof t !== 'function' || !p || typeof p !== 'object') return false;
        if (!BAR && t.prototype?.startMove && t.prototype?.endMove && t.contextType) BAR = t;
        if (!GRAB && 'target_mode' in p && 'min_distance' in p && !('parent_path' in p)) GRAB = t;
        return BAR && GRAB;
      }, 200000);
    }
    return BAR && GRAB;
  };
  // Where a scene-graph node is (the dashboard's own request, to SteamVR): from its module,
  // found by what it does (webpack's require, through a chunk of our own: no module numbers).
  let SG = null;
  const sg = () => {
    if (SG) return SG;
    try {
      let req = window.__sftWebpackRequire;
      if (!req) self.webpackChunkvrwebui.push([[Symbol(NAME)], {}, (r) => { req = window.__sftWebpackRequire = r; }]);
      const id = Object.keys(req.m).find((k) => String(req.m[k]).includes('type:"transform_request"'));
      const lib = id && req(id);
      const cls = lib && Object.values(lib).find((v) => typeof v === 'function' && v.prototype && 'requestSGTransform' in v.prototype);
      SG = cls?.getInstance?.() ?? null;
    } catch (e) { SG = null; }
    return SG;
  };
  const grabs = new Map();            // key -> {gen, held, landing: {t, until}}
  const nodeId = (key) => 'sftPanelGrab-' + key.replace(/[^A-Za-z0-9]/g, '_');
  const tell = (msg) => { try { window.sftPanelGrab?.(JSON.stringify(msg)); } catch (e) {} };
  const finite = (o, keys) => o && keys.every((k) => Number.isFinite(o[k]));
  const near = (a, b) => a && b && Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z) < 0.02;
  let mounted = null;
  const redraw = () => mounted?.redraw();

  const start = (key) => {
    const g = grabs.get(key);
    if (!g) return;
    g.held = true;
    g.landing = null;
    tell({ key, state: 'held' });
    redraw();
  };
  const end = (key) => {
    const g = grabs.get(key);
    if (!g?.held) return;
    g.held = false;
    g.landing = { until: Date.now() + LAND_MS };
    // (a moment for the grab transform to settle where it was let go)
    setTimeout(async () => {
      let t = null;
      try { t = await sg()?.requestSGTransform('system.systemui::' + nodeId(key), 0, 1); } catch (e) { t = null; }
      if (t?.translation && t?.rotation) {
        g.landing.t = t.translation;
        tell({ key, state: 'dropped', t: t.translation, r: t.rotation });
      } else {
        tell({ key, state: 'dropped' });           // (where it was: it stays)
        g.landing.until = 0;
      }
      redraw();
    }, 150);
    redraw();
  };
  // Landed: the panel is where its picture was let go (or it's taken too long): a fresh grab
  // transform, at the panel.
  const land = () => {
    const panels = window.__sftPanels ?? {};
    for (const [key, g] of grabs) {
      if (g.landing && (Date.now() > g.landing.until || near(panels[key]?.t, g.landing.t))) {
        g.landing = null;
        g.gen++;
        delete window.__sftPanelPictures?.[key];
      }
    }
  };

  const render = () => {
    land();
    const busy = [...grabs.values()].some((g) => g.held || g.landing);
    if (!(DS.m_bKeyboardVisible || busy) || !types()) return [];
    const { PANEL, XFORM } = L.components() ?? {};
    if (!PANEL) return [];
    const el = L.el, out = [];
    for (const [key, p] of Object.entries(window.__sftPanels ?? {})) {
      if (!(finite(p?.t, ['x', 'y', 'z']) && finite(p?.r, ['w', 'x', 'y', 'z']) && p.w > 0 && p.h > 0)) continue;
      if (!grabs.has(key)) grabs.set(key, { gen: 0, held: false, landing: null });
      const g = grabs.get(key), moving = g.held || g.landing;
      if (!p.visible && !moving) continue;
      const scale = Math.min(1, Math.max(0.5, 0.6 * p.w / BAR_M));
      const pic = window.__sftPanelPictures?.[key];
      out.push(el(XFORM, { key: `pg-${key}`, translation: p.t, rotation: p.r },
        el(GRAB, { key: `pg-${key}-${g.gen}`, min_distance: 0.2, max_distance: 3, target_mode: 1,
                   allow_scroll: true, scroll_speed: 8 },
          el(XFORM, { key: `pg-${key}-at`, id: nodeId(key) },
            moving ? el(PANEL, { key: `pg-${key}-pic`, width: p.w, interactive: false, only_visible_with_laser: false,
                                 debug_name: 'SftPanelGrabPicture', origin: L.ANCHOR.Center },
              pic ? el('img', { src: pic, style: { display: 'block', width: '400px', height: `${Math.round(400 * p.h / p.w)}px` } })
                  : el('div', { style: { width: '400px', height: `${Math.round(400 * p.h / p.w)}px`, boxSizing: 'border-box',
                                         border: '5px solid rgba(127, 178, 229, 0.95)', borderRadius: '10px',
                                         background: 'rgba(127, 178, 229, 0.15)' } })) : null),
          el(XFORM, { key: `pg-${key}-bar`, translation: { y: -p.h / 2 - BAR_M * scale * BAR_TALL - GAP_M } },
            el(BAR, { width: BAR_PX, scale, tint: DS.GrabHandleTint,
                      onStartMove: () => start(key), onEndMove: () => end(key) })))));
    }
    return out;
  };

  // The panels, from sft-dashboard, only while the keyboard shows (or a bar is busy).
  let wanted = null;
  const watchKeyboard = setInterval(() => {
    const want = !!DS.m_bKeyboardVisible || [...grabs.values()].some((g) => g.held || g.landing);
    if (want !== wanted) {
      wanted = want;
      try { window.sftPanels?.(JSON.stringify({ want })); } catch (e) {}
      redraw();
    }
  }, 300);
  mounted = L.mount('sft-panel-grab', render, 'right-mid', 300);
  if (!mounted) {
    clearInterval(watchKeyboard);
    return 'not patched: dashboard app component not found';
  }
  all[NAME] = {
    version: VERSION,
    redraw, panelsChanged: redraw,
    stop: () => {
      clearInterval(watchKeyboard);
      mounted.stop();
      for (const [key, g] of grabs) if (g.held || g.landing) tell({ key, state: 'dropped' });   // (shown again, where it was)
      try { window.sftPanels?.(JSON.stringify({ want: false })); } catch (e) {}
      delete window.__sftPanelPictures;
    },
  };
  return 'patched';
})()
