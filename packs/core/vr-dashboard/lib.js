// frame-tweaks dashboard helpers: what the patches share (window.__sftLib). sft-dashboard injects
// this before the patches, each time it injects them. Plumbing for finding and drawing things in
// SteamVR's dashboard page, and the tooltips the patches' icon buttons share (tip()).
// requires: window.Dashboard | window.Dashboard=
// requires: overlay picture size | GetOverlayMouseScale(
// requires: EDockLocation.Dashboard = 1 | .Dashboard=1]="Dashboard"
// requires: EDockLocation.World = 4 | .World=4]="World"
(() => {
  // sft-dashboard sets __sftLibWanted to this file's hash before injecting it: a changed lib.js
  // always replaces the one the dashboard has (a hand-kept number once wasn't bumped, and the
  // scroll strips' haptics called a function the loaded copy didn't have).
  const VERSION = window.__sftLibWanted ?? 2;
  if (window.__sftLib?.version === VERSION) return 'already loaded';
  // A patch keeps the lib.js it was injected with (L), and is injected again only when its own
  // VERSION changes: one injected just before a newer lib.js (they come from different tweaks'
  // installs) kept the old helpers, and Android Mirror's gear came without tooltips. So a lib.js
  // that replaces another clears every running patch's version: sft-dashboard injects the patches
  // right after this file, each sees a version not its own, stops its old copy and starts on this.
  const older = window.__sftLib;
  if (older) {
    try { older.stopTips?.(); } catch (e) {}
    for (const p of Object.values(window.__sftPatches ?? {})) if (p && typeof p === 'object') p.version = null;
  }
  const DOCK = { Dashboard: 1, World: 4 };
  // Panel anchors, for GetPanelAnchorID (a window has no Center anchor of its own).
  const ANCHOR = { TopCenter: 1, CenterLeft: 3, Center: 4, CenterRight: 5, BottomCenter: 7 };

  // Walk the dashboard's rendered React fibers; the first fiber visit() accepts, or null.
  const walk = (visit, limit = 50000) => {
    const rootEl = document.getElementById('root') ?? document.body.firstElementChild;
    const key = rootEl && Object.keys(rootEl).find((k) => k.startsWith('__reactContainer$'));
    if (!key) return null;
    const stack = [rootEl[key]];
    for (let n = 0; stack.length && n < limit; n++) {
      const fb = stack.pop();
      if (visit(fb)) return fb;
      if (fb.sibling) stack.push(fb.sibling);
      if (fb.child) stack.push(fb.child);
    }
    return null;
  };

  // The dashboard's scene-graph panel and transform components, found among its rendered fibers.
  let PANEL = null, XFORM = null;
  const components = () => {
    if (!(PANEL && XFORM)) {
      walk((fb) => {
        const p = fb.memoizedProps;
        if (p && typeof p === 'object' && typeof fb.type === 'function') {
          if (!PANEL && 'debug_name' in p && 'width' in p && 'interactive' in p) PANEL = fb.type;
          if (!XFORM && 'parent_id' in p && 'translation' in p && !('width' in p)) XFORM = fb.type;
        }
        return PANEL && XFORM;
      });
    }
    return PANEL && XFORM ? { PANEL, XFORM } : null;
  };

  // React elements, made like the dashboard's own (copied from one of its elements: the page
  // has no global React to call createElement on).
  let SAMPLE = null;
  const el = (type, props, ...children) => {
    const e = Object.assign({}, SAMPLE, { type, key: props?.key ?? null,
      props: Object.assign({}, props, children.length ? { children: children.length === 1 ? children[0] : children } : {}) });
    if ('_store' in e) e._store = {};
    if ('ref' in e && !('ref' in (props ?? {}))) e.ref = null;
    return e;
  };

  // A window's picture size {w, h}, from its overlay (the page's own latestContentSize is only
  // read again when something else changes, so it can keep an old shape).
  const pictureSize = (page) => {
    try {
      const m = VRHTML.VROverlay.GetOverlayMouseScale(VRHTML.VROverlay.FindOverlay(page.summonOverlayKey));
      if (m?.x > 0 && m?.y > 0) return { w: m.x, h: m.y };
    } catch (e) { /* no overlay */ }
    const c = page?.size?.latestContentSize;
    return c?.unWidth > 0 && c?.unHeight > 0 ? { w: c.unWidth, h: c.unHeight } : null;
  };

  // memo(): a small cache, so a patch hands the dashboard the very same pieces while nothing
  // they show has changed (fresh copies, even identical ones, get sent to SteamVR again).
  const memo = (max = 40) => {
    const m = new Map();
    return (key, make) => {
      if (m.has(key)) return m.get(key);
      const v = make();
      m.set(key, v);
      if (m.size > max) m.delete(m.keys().next().value);
      return v;
    };
  };

  // Our pieces are drawn from the dashboard's one shared page (about 1860 x 2048). Placed after
  // its own content they moved whenever that changed size, which showed as jitter, and tall ones
  // ran off the page: each patch gets a fixed spot of its own. A panel shows whatever the page
  // has at its spot, so two patches sharing one showed each other's pieces. 'left' and 'right':
  // the bottom corners (the scroll strips; Android Mirror's pieces); 'right-mid': the right
  // side, 900 px up (panel-grab), between those and the dashboard's own controls at the top.
  const area = (side) => {
    const [edge, up] = side === 'right-mid' ? ['right', '900px'] : [side, '0px'];
    return { position: 'absolute', bottom: up, width: '920px', [edge]: '0px', textAlign: edge === 'right' ? 'right' : 'left' };
  };

  // ---- tooltips ----
  // tip(text): props for a button whose face has no word on it (spread them in:
  // el('div', { ...tap(), onClick, ...L.tip(T(label)) }, '✕')). A title: alone shows nothing in
  // the headset: Chromium draws title tooltips in a popup window of their own, and the dashboard
  // shows only what the page draws at each panel's spot. So the text gets a small panel of its own,
  // just above the button and a little in front of it, drawn from the page above the corner of
  // the mount (mount()) whose panel holds the button. Timed as the desktop window's tooltips
  // (lib/tooltips.py): after 700 ms on the button; the laser's wobble doesn't start the wait again
  // (moves on the button never do, and leaving it for less than TIP.GRACE_MS doesn't either);
  // gone on leaving it or on a press, and after twice Qt's time (20 s, longer for long texts).
  // Not React's onPointerEnter / onPointerLeave: the laser's pointerover events reached the page
  // (482 in a few minutes) but never started a wait through them. So: any over or move on the
  // button (bubbling up from its svg too) is "on it", and one listener on the window, in the
  // capture phase (before own()'s stopPropagation), sees the pointer land anywhere else (a leave),
  // leave the page, or press. Over and move only on the button, mouse and pointer both: the
  // patches' own onMouseEnter / onMouseDown (haptics, own()) keep theirs.
  const TIP = { WAIT_MS: 700, GRACE_MS: 150, REVEAL_MS: 120,
                // (20 px at 1 mm: 2 cm letters; 1 cm was too small, tried in VR)
                FONT_PX: 20, PAD_PX: 10, MAX_PX: 560, M_PER_PX: 0.001,
                GAP_M: 0.012, LIFT_M: 0.004 };
  const tipMs = (text) => 2 * (10000 + 40 * Math.max(0, text.length - 100));   // (qt_default_ms, twice)
  const tips = { on: null, text: '', wait: 0, grace: 0, hide: 0, shown: null, n: 0,
                 seen: { starts: 0, leaves: 0, presses: 0, shows: 0, unplaced: 0 } };     // (tipState())
  const redraws = new Map();             // mount key -> redraw (mount())
  const fiberOf = (node) => {
    const k = node && Object.keys(node).find((n) => n.startsWith('__reactFiber$') || n.startsWith('__reactInternalInstance$'));
    return k ? node[k] : null;
  };
  // Anchor units per metre where a panel hangs (a window's anchors are in its own scaled units:
  // the patches' k): the window whose page gave that anchor id. null: none of them did.
  const unitsPerMetre = (anchorId) => {
    for (const f of window.FrameStore?.frames ?? []) {
      const page = f?.activePage, sz = page?.size;
      if (typeof page?.GetPanelAnchorID !== 'function' || !(sz?.latestMeasuredPanelWorldHeight > 0)) continue;
      for (const a of Object.values(ANCHOR)) {
        try {
          if (page.GetPanelAnchorID(a) === anchorId) return sz.latestMeasuredPanelLocalHeight / sz.latestMeasuredPanelWorldHeight;
        } catch (e) { break; }
      }
    }
    return null;
  };
  let measure = null;
  const fontFamily = () => { try { return getComputedStyle(document.body).fontFamily || 'sans-serif'; } catch (e) { return 'sans-serif'; } };
  const textPx = (text, family) => {
    try {
      measure ??= document.createElement('canvas').getContext('2d');
      measure.font = `${TIP.FONT_PX}px ${family}`;
      return measure.measureText(text).width;
    } catch (e) { return text.length * TIP.FONT_PX * 0.55; }
  };
  const tintHue = () => {
    try {
      const h = window.VRSettingsState?.settings?.get('/settings/camera/monochromeTintHue');
      if (typeof h === 'number' && isFinite(h)) return Math.round(((h % 1) + 1) % 1 * 360);
    } catch (e) {}
    return 210;
  };
  // Where the tooltip for this button goes: from its React fibers up, its panel (PANEL: width,
  // origin, curvature), the transform that places that panel (XFORM: parent_id, translation) and
  // the mount drawing them. The button's place in its panel is its place in the panel's top
  // element, so nothing is asked of the patches. null: not in one of our panels as expected.
  const place = (target, text) => {
    const c = components();
    if (!c) return null;
    let fb = fiberOf(target), panel = null, xf = null, owner = null;
    const hosts = [];
    for (let n = 0; fb && n < 400 && !owner; n++, fb = fb.return) {
      if (!panel) { if (fb.type === c.PANEL) panel = fb; else if (typeof fb.type === 'string') hosts.push(fb); }
      else if (!xf) { if (fb.type === c.XFORM) xf = fb; }
      else if (typeof fb.type === 'function' && fb.type.sftMount) owner = fb.type.sftMount;
    }
    const P = panel?.memoizedProps, X = xf?.memoizedProps;
    // (a turned transform, or one nested in another, would need its whole chain: none of ours is;
    // a rotation of nothing, as a default could give, is no turn)
    const turned = X?.rotation && ['x', 'y', 'z'].some((a) => Math.abs(X.rotation[a] ?? 0) > 1e-6);
    if (!owner || !(P?.width > 0) || X?.parent_id == null || turned) return null;
    const top = hosts.find((h) => h.memoizedProps === P.children?.props) ?? hosts[hosts.length - 1];
    const r = top?.stateNode?.getBoundingClientRect?.(), b = target.getBoundingClientRect?.();
    if (!(r?.width > 0 && r?.height > 0 && b)) return null;
    // (both rects as the page lays them out, a zoom included: only their ratio counts)
    const W = P.width, s = W / r.width, H = r.height * s, o = P.origin ?? ANCHOR.Center;
    const t = X.translation ?? {};
    const left = (t.x ?? 0) - (o % 3) * W / 2, upper = (t.y ?? 0) + Math.floor(o / 3) * H / 2;      // (its edges)
    // (no window gave that anchor: about the size the patches draw their panels at, 1.2 mm a pixel)
    const k = unitsPerMetre(X.parent_id) ?? s / 0.0012;
    const family = fontFamily();
    const px = Math.min(TIP.MAX_PX, Math.ceil(textPx(text, family)) + 2 * TIP.PAD_PX + 8);
    const at = { x: left + (b.left + b.width / 2 - r.left) * s, y: upper - (b.top - r.top) * s + TIP.GAP_M * k,
                 // in front of the button, and of the window's plane (Scroll strips' gear is set back behind it)
                 z: Math.max(t.z ?? 0, 0) + TIP.LIFT_M * k };
    const h = tintHue(), n = ++tips.n;
    const piece = (ready) => el('div', { key: `sft-tip-${n}`, style: { position: 'absolute', bottom: '100%', pointerEvents: 'none',
                                                                    [owner.side === 'left' ? 'left' : 'right']: '0px' } },
      el(c.XFORM, { key: `sft-tip-${n}-x`, parent_id: X.parent_id, translation: at },
        el(c.PANEL, { key: `sft-tip-${n}-p`, width: px * TIP.M_PER_PX * k, interactive: false, only_visible_with_laser: false,
                      debug_name: 'SftTooltip', origin: ANCHOR.BottomCenter,
                      ...(P.curvature_origin_id ? { curvature_origin_id: P.curvature_origin_id } : {}) },
          el('div', { style: { width: `${px}px`, boxSizing: 'border-box', padding: `6px ${TIP.PAD_PX}px`, borderRadius: '10px',
                               background: 'rgba(22, 27, 34, 0.94)', border: `1px solid hsla(${h}, 60%, 68%, 0.6)`,
                               color: '#e8ecf0', fontFamily: family, fontSize: `${TIP.FONT_PX}px`, lineHeight: 1.3,
                               textAlign: 'center', whiteSpace: 'normal', overflowWrap: 'anywhere', opacity: ready ? 1 : 0 } },
            text))));
    return { owner: owner.key, target, at, width: px * TIP.M_PER_PX * k, text, ready: false,
             pieces: [piece(false), piece(true)] };
  };
  const redrawTip = (key) => redraws.get(key)?.();
  const hideTip = () => {
    clearTimeout(tips.hide);
    const s = tips.shown;
    tips.shown = null;
    if (s) redrawTip(s.owner);
  };
  const dropTip = () => {           // (and forget the button: only entering one starts a wait)
    clearTimeout(tips.wait); clearTimeout(tips.grace);
    tips.on = null;
    hideTip();
  };
  const wakeTip = () => {
    const target = tips.on;
    if (!target || target.isConnected === false) return dropTip();
    // (the title as it is now: a button's text can change with its state, the gear's on opening)
    const text = target.getAttribute?.('title') || tips.text;
    const s = text && place(target, text);
    if (!s) { tips.seen.unplaced++; return; }
    tips.seen.shows++;
    tips.shown = s;
    redrawTip(s.owner);
    // Its first drawing see-through: a panel made anew can be drawn for a moment somewhere else
    // first (phone-touch.js's hwKeys saw it in the middle of the mirror).
    setTimeout(() => { if (tips.shown === s) { s.ready = true; redrawTip(s.owner); } }, TIP.REVEAL_MS);
    tips.hide = setTimeout(hideTip, tipMs(text));
  };
  const tipHere = (target, text) => {
    if (tips.on === target) { clearTimeout(tips.grace); tips.grace = 0; return; }   // (back within the grace: as if never gone)
    dropTip();
    tips.seen.starts++;
    tips.on = target;
    tips.text = text;
    tips.wait = setTimeout(wakeTip, TIP.WAIT_MS);
  };
  const tipLeave = () => {
    if (!tips.on || tips.grace) return;          // (the first leave counts: later moves don't put it off)
    tips.seen.leaves++;
    tips.grace = setTimeout(dropTip, TIP.GRACE_MS);
  };
  const tipPress = () => {          // (gone, and not back until the laser leaves and comes again)
    tips.seen.presses++;
    clearTimeout(tips.wait);
    hideTip();
  };
  const watchTips = (ev) => {
    const on = tips.on;
    if (!on) return;
    let inside = false;
    try { inside = !!ev.target && on.contains(ev.target); } catch (e) {}
    const type = ev.type;
    if (type === 'pointerdown' || type === 'mousedown') { if (inside) tipPress(); }
    else if (type === 'pointerout' || type === 'mouseout') { if (!ev.relatedTarget) tipLeave(); }   // (off the page)
    else if (!inside) tipLeave();
  };
  const WATCHED = ['pointerover', 'pointermove', 'mouseover', 'mousemove', 'pointerout', 'mouseout', 'pointerdown', 'mousedown'];
  try { for (const t of WATCHED) window.addEventListener(t, watchTips, true); } catch (e) {}
  const stopTips = () => {          // (a newer lib.js takes over: one watcher on the page at a time)
    try { for (const t of WATCHED) window.removeEventListener(t, watchTips, true); } catch (e) {}
    dropTip();
  };
  const tip = (text) => {
    const here = (ev) => tipHere(ev.currentTarget, text);
    return { title: text,           // (kept: a desktop browser on the DevTools port still shows it)
             onPointerOver: here, onPointerMove: here, onMouseOver: here, onMouseMove: here };
  };
  // The tooltip piece for the mount `key`, or null: mount() adds it after the patch's own pieces.
  // Outside the corner's flow (just above it, at its edge), so they don't move for it.
  const tipFor = (key) => {
    const s = tips.shown;
    if (!s || s.owner !== key) return null;
    if (s.target.isConnected === false) { tips.shown = null; return null; }   // (its panel went: a press, a redraw)
    return s.pieces[s.ready ? 1 : 0];
  };

  // mount(key, render, side): draw render() (an array of pieces, or null) as the last child of
  // the dashboard app, redrawn every `every` ms and on redraw(); in the page corner `side`. Puts
  // itself back (a few times) if something drops it from the app's render. Returns {redraw, stop}.
  const mount = (key, render, side, every = 500) => {
    const D = window.Dashboard;
    const Base = D && Object.getPrototypeOf(D.constructor);
    if (!Base?.prototype?.isReactComponent) return null;
    const app = walk((fb) => fb.stateNode && typeof fb.stateNode.toggleDebugPointer === 'function')?.stateNode;
    if (!app) return null;
    let on = true, mounted = 0, inst = null, wrapped = null, tries = 0;
    class Holder extends Base {
      // (how a hovered button's tooltip finds the mount whose corner of the page draws it: tip())
      static sftMount = { key, side };
      componentDidMount() { mounted++; inst = this; this.timer = setInterval(() => { try { this.forceUpdate(); } catch (e) {} }, every); }
      componentWillUnmount() { mounted--; if (inst === this) inst = null; clearInterval(this.timer); }
      render() {
        try {
          if (!on || !components()) return null;
          const parts = (render() ?? []).filter(Boolean);
          const t = tipFor(key);
          if (parts.length && t) parts.push(t);
          return parts.length ? el('div', { key: `${key}-area`, style: area(side) }, ...parts) : null;
        } catch (e) { return null; }
      }
    }
    const redrawTip = () => { try { inst?.forceUpdate(); } catch (e) {} };
    redraws.set(key, redrawTip);
    const attach = () => {
      const below = app.render;
      wrapped = app.render = function (...args) {
        const tree = below.apply(this, args);
        const kids = tree?.props?.children;
        if (!on || !tree || typeof tree !== 'object' || !Array.isArray(kids)) return tree;
        SAMPLE ??= tree;
        return Object.assign({}, tree, { props: Object.assign({}, tree.props, { children: [...kids, el(Holder, { key })] }) });
      };
      try { app.forceUpdate(); } catch (e) {}
    };
    attach();
    // Not mounted: wrap the render again only if ours isn't it any more, and three times at most
    // until it mounts (it wrapped every 2 s for as long as it wasn't, a layer deeper each time).
    const guard = setInterval(() => {
      if (mounted) tries = 0;
      else if (on && app.render !== wrapped && tries < 3) { tries++; attach(); }
    }, 2000);
    return {
      redraw: () => { try { inst?.forceUpdate(); } catch (e) {} },
      // (stays in the render chain, passing straight through: unwrapping could drop another's)
      stop: () => { on = false; clearInterval(guard);
                   if (redraws.get(key) === redrawTip) redraws.delete(key);
                   try { app.forceUpdate(); } catch (e) {} },
    };
  };

  // The dashboard's own controller haptics (what its buttons and sliders use): a tick on the
  // controller pointing at this overlay. Optional: does nothing if SteamVR's page API changes.
  const HAPTIC = { Enter: 1, Leave: 2, Snap: 3, Sliding: 4, SlidingEdge: 5 };
  const haptic = (effect) => {
    try {
      if (typeof VRHTML !== 'undefined' && VRHTML && VRHTML.VROverlay)
        VRHTML.VROverlay.TriggerOverlayHapticEffect(VRHTML.VROverlay.ThisOverlayHandle(), effect);
    } catch (e) {}
  };

  // tick('Enter'): haptic by name, for patches (which look it up at each call, as window.__sftLib?.tick:
  // this file can be replaced while they run).
  const tick = (name) => haptic(HAPTIC[name]);

  // tipState(): what the tooltips are doing, for a look over the DevTools port.
  const tipState = () => ({ waiting: !!tips.on && !tips.shown, seen: { ...tips.seen },
                            shown: tips.shown && { text: tips.shown.text, owner: tips.shown.owner, at: tips.shown.at,
                                                   width: tips.shown.width, ready: tips.shown.ready } });

  window.__sftLib = { version: VERSION, DOCK, ANCHOR, walk, components, el, pictureSize, memo, mount, HAPTIC, haptic, tick,
                      tip, tipFor, tipState, stopTips };
  return 'loaded';
})()
