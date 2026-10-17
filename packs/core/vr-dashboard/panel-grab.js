// frame-tweaks panel-grab: SteamVR's own grab bar under each Frame Tweaks panel in VR (Arrow Pad,
// Screen snip's narration panel) while Steam's keyboard is open, to move it anywhere.
// While the keyboard shows, SteamVR hides where the controllers are from other programs (its
// keyboard privacy), so a panel can't follow the hand that grabs it: it only slides after the
// laser. SteamVR's dashboard still moves things: this puts the bar it draws under its windows
// under the panel, and moves the panel as the dashboard moves a window floating in the world.
// Held, the panel hides and a picture of it is pinned to the hand (rigidly: turned and tilted
// with it), in a grab-scale node (the stick pushes it away or pulls it closer); let go, SteamVR
// says where the picture is, the panel is told (by sft-dashboard: lib/vrkit.py DashboardGrab),
// and takes its place. The hand's pose is read here, in the dashboard, as the dashboard reads it
// for its windows: none leaves it, only where the panel was let go.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard, which installs it.
// requires: the grab bar | debug_name:"GrabHandle"
// requires: grabbing it | startMove(e){let t;switch(
// requires: what it tells its context | this.context.setState({parent_path:t})
// requires: the hand's pose | VRHTML.GetPose(
// requires: windows pinned to the hand | this.m_sUnpushedOriginID
// requires: the stick pushing them | return"grab-scale"
// requires: asking where a node is | type:"transform_request"
// requires: the scene graph's requests | requestSGTransform(e){
// requires: the page's modules | webpackChunkvrwebui
// requires: Steam's keyboard showing | this.m_bKeyboardVisible=e.visible
(() => {
  const NAME = 'panel-grab', VERSION = 2;
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const L = window.__sftLib, DS = window.DashboardStore;
  if (!L || !DS) return 'not patched: dashboard pieces not found';
  // The bar's panel at scale 1, width 350: 0.333 m wide, 0.28 as tall as wide, its origin its
  // bottom centre, the bar across its middle (its picture is 470 x 132 px).
  const BAR_PX = 350, BAR_M = 0.66675 * BAR_PX / 700, BAR_TALL = 132 / 470, GAP_M = 0.005;
  const LAND_MS = 1500;                // the picture stays where it was let go until the panel is there
  const STANDING = 1;                  // ETrackingUniverseOrigin: the dashboard's world (checked: 1 mm)

  // The dashboard's grab bar: GrabHandle (startMove/endMove), which tells its context (a grab
  // transform's, under SteamVR's own bar) which hand holds it: here, ours.
  let BAR = null;
  const bar = () => {
    if (!BAR) {
      L.walk((fb) => {
        const t = fb.type;
        if (typeof t === 'function' && t.prototype?.startMove && t.prototype?.endMove && t.contextType?.Provider) BAR = t;
        return !!BAR;
      }, 200000);
    }
    return BAR;
  };
  // From the page's modules, found by what they do (webpack's require, through a chunk of our
  // own: no module numbers): the grab-scale node (a floating window's stick push) and the scene
  // graph's requests (where a node is).
  let REQ = null;
  const modules = (has) => {
    try {
      if (!REQ) self.webpackChunkvrwebui.push([[Symbol(NAME)], {}, (r) => { REQ = r; }]);
      const id = Object.keys(REQ.m).find((k) => String(REQ.m[k]).includes(has));
      return id ? Object.values(REQ(id)) : [];
    } catch (e) { return []; }
  };
  let SCALE, SG;
  const grabScale = () => (SCALE ??= modules('return"grab-scale"').find((v) => {
    try { return typeof v === 'function' && v.prototype?.getNodeType?.() === 'grab-scale'; } catch (e) { return false; }
  }) ?? null);
  const sg = () => (SG ??= modules('type:"transform_request"')
    .find((v) => typeof v === 'function' && v.prototype && 'requestSGTransform' in v.prototype)?.getInstance?.() ?? null);

  // Rigid transforms as the dashboard has them: {translation {x,y,z}, rotation {w,x,y,z}}.
  const qmul = (a, b) => ({ w: a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z, x: a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
                            y: a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x, z: a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w });
  const conj = (q) => ({ w: q.w, x: -q.x, y: -q.y, z: -q.z });
  const turn = (q, v) => { const r = qmul(qmul(q, { w: 0, ...v }), conj(q)); return { x: r.x, y: r.y, z: r.z }; };
  const relative = (h, p) => {        // p seen from h: h^-1 * p
    const inv = conj(h.rotation);
    return { translation: turn(inv, { x: p.translation.x - h.translation.x, y: p.translation.y - h.translation.y,
                                      z: p.translation.z - h.translation.z }),
             rotation: qmul(inv, p.rotation), scale: { x: 1, y: 1, z: 1 } };
  };
  const handPose = (path) => {
    try {
      const [p] = VRHTML.GetPose(path, STANDING);
      return p?.bPoseIsValid ? p.xfDeviceToAbsoluteTracking : null;
    } catch (e) { return null; }
  };

  const grabs = new Map();            // key -> {gen, held: {hand, rel}, landing: {pose, until}, sgid, ctl}
  const nodeId = (key) => 'sftPanelGrab-' + key.replace(/[^A-Za-z0-9]/g, '_');
  const tell = (msg) => { try { window.sftPanelGrab?.(JSON.stringify(msg)); } catch (e) {} };
  const finite = (o, keys) => o && keys.every((k) => Number.isFinite(o[k]));
  const near = (a, b) => a && b && Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z) < 0.02;
  let mounted = null;
  const redraw = () => mounted?.redraw();

  // The bar held (by a hand, its path) and let go (''), as it tells its context.
  const start = (key, hand) => {
    const g = grabs.get(key), p = window.__sftPanels?.[key], h = handPose(hand);
    if (!g || !p || !h || g.held) return;
    g.held = { hand, rel: relative(h, { translation: p.t, rotation: p.r }) };
    g.landing = null;
    tell({ key, state: 'held' });
    redraw();
  };
  const end = async (key) => {
    const g = grabs.get(key);
    if (!g?.held) return;
    let t = null;
    try { t = await sg()?.requestSGTransform('system.systemui::' + nodeId(key), 0, 1); } catch (e) { t = null; }
    g.held = null;
    g.gen++;                                       // (the stick's push starts afresh next time)
    if (t?.translation && t?.rotation) {
      g.landing = { pose: { t: t.translation, r: t.rotation }, until: Date.now() + LAND_MS };
      tell({ key, state: 'dropped', t: t.translation, r: t.rotation });
    } else {
      g.landing = null;
      tell({ key, state: 'dropped' });             // (where it was: it stays)
    }
    redraw();
  };
  const entry = (key) => {
    if (!grabs.has(key)) {
      const g = { gen: 0, held: null, landing: null, sgid: undefined };
      g.ctl = { setState: (st) => {                 // (what GrabHandle tells a grab transform)
        if ('event_panel_sgid' in st) g.sgid = st.event_panel_sgid;
        if ('parent_path' in st) st.parent_path ? start(key, st.parent_path) : end(key);
      } };
      grabs.set(key, g);
    }
    return grabs.get(key);
  };
  // Landed: the panel is where its picture was let go (or it's taken too long).
  const land = () => {
    const panels = window.__sftPanels ?? {};
    for (const [key, g] of grabs) {
      if (g.landing && (Date.now() > g.landing.until || near(panels[key]?.t, g.landing.pose.t))) {
        g.landing = null;
        delete window.__sftPanelPictures?.[key];
      }
    }
  };

  const render = () => {
    land();
    const busy = [...grabs.values()].some((g) => g.held || g.landing);
    if (!(DS.m_bKeyboardVisible || busy) || !bar()) return [];
    const { PANEL, XFORM } = L.components() ?? {};
    if (!PANEL) return [];
    const el = L.el, GS = grabScale(), out = [];
    for (const [key, p] of Object.entries(window.__sftPanels ?? {})) {
      if (!(finite(p?.t, ['x', 'y', 'z']) && finite(p?.r, ['w', 'x', 'y', 'z']) && p.w > 0 && p.h > 0)) continue;
      const g = entry(key), moving = g.held || g.landing;
      if (!p.visible && !moving) continue;
      const scale = Math.min(1, Math.max(0.5, 0.6 * p.w / BAR_M));
      const pic = window.__sftPanelPictures?.[key];
      const at = g.landing?.pose ?? p;
      // Held: pinned to the hand, as a floating window is; otherwise where the panel is.
      const where = g.held ? { parent_path: g.held.hand, transform: g.held.rel } : { translation: at.t, rotation: at.r };
      const d = g.held ? Math.hypot(g.held.rel.translation.x, g.held.rel.translation.y, g.held.rel.translation.z) : undefined;
      const inside = [
        el(XFORM, { key: `pg-${key}-at`, id: nodeId(key) },
          moving ? el(PANEL, { key: `pg-${key}-pic`, width: p.w, interactive: false, only_visible_with_laser: false,
                               debug_name: 'SftPanelGrabPicture', origin: L.ANCHOR.Center },
            pic ? el('img', { src: pic, style: { display: 'block', width: '400px', height: `${Math.round(400 * p.h / p.w)}px` } })
                : el('div', { style: { width: '400px', height: `${Math.round(400 * p.h / p.w)}px`, boxSizing: 'border-box',
                                       border: '5px solid rgba(127, 178, 229, 0.95)', borderRadius: '10px',
                                       background: 'rgba(127, 178, 229, 0.15)' } })) : null),
        el(XFORM, { key: `pg-${key}-bar`, translation: { y: -p.h / 2 - BAR_M * scale * BAR_TALL - GAP_M } },
          el(BAR.contextType.Provider, { value: g.ctl },
            el(BAR, { width: BAR_PX, scale, tint: DS.GrabHandleTint }))),
      ];
      out.push(el(XFORM, { key: `pg-${key}`, ...where },
        GS ? el(GS, { key: `pg-${key}-gs`, is_active: !!g.held, event_panel_sgid: g.held ? g.sgid : undefined,
                      base_distance: d, min_distance: 0.25, max_distance: 5, scroll_speed: 10, reset_generation: g.gen }, ...inside)
           : inside));
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
