// steam-frame-tweaks scroll-strips: big scroll strips beside each window (the one docked in the
// dashboard and every floating one), easy to hit with
// the laser. Drag along a strip to scroll (like dragging a scroll bar); tap near either end to
// page. Scrolling goes to the window you last clicked (SteamVR gives the dashboard no way to
// scroll a particular window), through vr-dashboard's sftScroll binding: real wheel steps in the
// desktop (its Remote Desktop portal), arrow keys / PgUp-PgDn in other windows.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard. Settings:
// window.__sftPatchConfig["scroll-strips"] = {vertical: "right"|"left"|"off",
//   horizontal: "top"|"bottom"|"off", thickness: metres, gap: metres}. Sizes are real metres (the
// floating window's own space); the page elements stay small, so the dashboard's layout is unchanged.
// (Version 1 used the window's scaled local size and big page elements: strips far too big and far
// away, and the Steam bar drawn too large.)
// requires: panel anchors | GetPanelAnchorID(e){
// requires: frame panel height | latestMeasuredPanelLocalHeight
// requires: window.Dashboard | window.Dashboard=
// requires: EDockLocation.Dashboard = 1 | e[e.Dashboard=1]="Dashboard"
// requires: EDockLocation.World = 4 | e[e.World=4]="World"
(() => {
  // Each strip hangs off its window panel's edge anchor (GetPanelAnchorID: CenterRight / CenterLeft /
  // TopCenter / BottomCenter), so it follows the window wherever it is, docked or floating. A small
  // component of our own draws them; it's mounted beside the dashboard's root (window.Dashboard).
  const NAME = 'scroll-strips', VERSION = 7, DASH = 1, WORLD = 4;
  const ANCHOR = { CenterLeft: 3, CenterRight: 5, TopCenter: 1, BottomCenter: 7, Center: 4 };
  const NOTCHES_PER_LENGTH = 40;     // a drag along the whole strip scrolls this many wheel notches
  const PAGE = 10;                   // notches for a tap near an end
  const IDLE_END_MS = 800;           // the laser's release doesn't always arrive: end after this still
  const stats = { downs: 0, moves: 0, ups: 0, sent: 0, noBinding: 0 };   // for diagnosis
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore, DS = window.DashboardStore, D = window.Dashboard;
  if (!FS || !DS || !D) return 'not patched: dashboard objects missing';
  const Base = Object.getPrototypeOf(D.constructor);
  if (!Base?.prototype?.isReactComponent) return 'not patched: no React component class';
  const cfg = () => {
    const c = { vertical: 'right', horizontal: 'top', thickness: 0.04, gap: 0.015, ...(window.__sftPatchConfig?.[NAME] ?? {}) };
    c.thickness = Math.min(0.1, Math.max(0.015, Number(c.thickness) || 0.04));
    c.gap = Math.min(0.1, Math.max(0, Number(c.gap) || 0.015));
    return c;
  };

  // The dashboard's panel and transform components, found among its rendered fibers.
  const fibers = () => {
    const rootEl = document.getElementById('root');
    const key = rootEl && Object.keys(rootEl).find((k) => k.startsWith('__reactContainer$'));
    return key ? [rootEl[key]] : [];
  };
  let PANEL = null, XFORM = null, SAMPLE = null;
  const learn = () => {
    const stack = fibers();
    while (stack.length && !(PANEL && XFORM)) {
      const fb = stack.pop(), p = fb.memoizedProps;
      if (p && typeof p === 'object' && typeof fb.type === 'function') {
        if (!PANEL && 'debug_name' in p && 'width' in p && 'interactive' in p) PANEL = fb.type;
        if (!XFORM && 'parent_id' in p && 'translation' in p && !('width' in p)) XFORM = fb.type;
      }
      if (fb.sibling) stack.push(fb.sibling);
      if (fb.child) stack.push(fb.child);
    }
    return PANEL && XFORM;
  };
  const el = (type, props, ...children) => {
    const e = Object.assign({}, SAMPLE, { type, key: props?.key ?? null,
      props: Object.assign({}, props, children.length ? { children: children.length === 1 ? children[0] : children } : {}) });
    if ('_store' in e) e._store = {};
    if ('ref' in e && !('ref' in (props ?? {}))) e.ref = null;
    return e;
  };

  let drag = null;
  const send = (target, dx, dy, page = 0) => {
    if (typeof window.sftScroll !== 'function') { stats.noBinding++; return; }
    try { window.sftScroll(JSON.stringify({ target, dx, dy, page })); stats.sent++; } catch (e) {}
  };
  const onMove = (ev) => {
    if (!drag) return;
    stats.moves++;
    clearTimeout(drag.idle);
    drag.idle = setTimeout(() => onUp(), IDLE_END_MS);
    const pos = drag.axis === 'y' ? ev.clientY : ev.clientX;
    drag.moved = Math.max(drag.moved, Math.abs(pos - drag.start));
    const want = Math.trunc(((pos - drag.start) / drag.length) * NOTCHES_PER_LENGTH);
    const step = want - drag.sent;
    if (step) {
      drag.sent = want;
      // Scroll-bar sense: drag down (or right) scrolls down (or right). Wheel: +y is up.
      drag.axis === 'y' ? send(drag.target, 0, -step) : send(drag.target, step, 0);
    }
  };
  const onUp = () => {
    stats.ups++;
    window.removeEventListener('mousemove', onMove, true);
    window.removeEventListener('mouseup', onUp, true);
    window.removeEventListener('pointerup', onUp, true);
    const d = drag; drag = null;
    if (d) clearTimeout(d.idle);
    if (!d || d.moved > d.length * 0.03) return;
    const at = (d.start - d.from) / d.length;                    // a tap: near an end pages
    if (d.axis === 'y') {
      if (at < 0.25) send(d.target, 0, 0, 1);
      else if (at > 0.75) send(d.target, 0, 0, -1);
    } else if (at < 0.25) send(d.target, -PAGE, 0);
    else if (at > 0.75) send(d.target, PAGE, 0);
  };
  const strip = (key, axis, length, thick, target, curveId) => {   // sizes in the anchor's units
    const px = 16, lenPx = Math.min(600, Math.round(px * length / thick));   // small page elements
    const style = { width: `${axis === 'y' ? px : lenPx}px`, height: `${axis === 'y' ? lenPx : px}px`,
      background: 'rgba(40, 50, 62, 0.55)', borderRadius: `${px / 2}px`, boxSizing: 'border-box',
      border: '1px solid rgba(127, 178, 229, 0.6)' };
    return el(PANEL, { key, width: axis === 'y' ? thick : length, interactive: true, only_visible_with_laser: false,
      debug_name: `SftScroll${axis.toUpperCase()}`, origin: ANCHOR.Center, inputFocusParams: { bCanTakeKeyboardFocus: false },
      ...(curveId ? { curvature_origin_id: curveId } : {}) },
      el('div', { style, onMouseDown: (ev) => {
        stats.downs++;
        if (drag) onUp();                         // a new press ends any drag still open
        const r = ev.currentTarget.getBoundingClientRect();
        drag = { axis, target, start: axis === 'y' ? ev.clientY : ev.clientX, from: axis === 'y' ? r.top : r.left,
                 length: axis === 'y' ? r.height : r.width, sent: 0, moved: 0 };
        window.addEventListener('mousemove', onMove, true);
        window.addEventListener('mouseup', onUp, true);
        window.addEventListener('pointerup', onUp, true);
      } }));
  };
  const stripsFor = (f) => {
    const page = f?.activePage, sz = page?.size;
    const H = sz?.latestMeasuredPanelLocalHeight, Hw = sz?.latestMeasuredPanelWorldHeight, c = sz?.latestContentSize;
    if (!H || !Hw || !c?.unHeight || typeof page.GetPanelAnchorID !== 'function') return [];
    const o = cfg(), k = H / Hw;                 // anchor units per metre (the panel's own scale)
    // The desktop scrolls through its own portal; other windows get keys (see vr-dashboard).
    const target = /^KDE Wayland Compositor/.test(f.title ?? '') ? 'desktop' : 'window';
    // A curved window: bend the horizontal strip around the same origin as the window.
    const curveId = f.curvature?.shouldCurve ? f.curvature.curvatureTransformOriginID : undefined;
    const W = H * c.unWidth / c.unHeight, t = o.thickness * k, g = o.gap * k, out = [];
    const at = (anchor, translation, child) => {
      const id = page.GetPanelAnchorID(anchor);
      return id ? el(XFORM, { key: `${f.frameID}-${anchor}`, parent_id: id, translation }, child) : null;
    };
    if (o.vertical !== 'off') {
      const left = o.vertical === 'left';
      out.push(at(left ? ANCHOR.CenterLeft : ANCHOR.CenterRight, { x: (left ? -1 : 1) * (g + t / 2) },
                  strip(`${f.frameID}-y`, 'y', H, t, target)));
    }
    if (o.horizontal !== 'off') {
      const bottom = o.horizontal === 'bottom';
      out.push(at(bottom ? ANCHOR.BottomCenter : ANCHOR.TopCenter, { y: (bottom ? -1 : 1) * (g + t / 2) },
                  strip(`${f.frameID}-x`, 'x', W, t, target, curveId)));
    }
    return out.filter(Boolean);
  };

  class SftScrollStrips extends Base {
    componentDidMount() { this.timer = setInterval(() => { try { this.forceUpdate(); } catch (e) {} }, 500); }
    componentWillUnmount() { clearInterval(this.timer); }
    render() {
      try {
        if (!learn()) return null;
        const out = [];
        for (const f of FS.frames ?? []) {
          const dock = f?.docking?.dockLocation;
          if (dock === WORLD || (dock === DASH && f === DS.activeFrame && DS.isFullyVisible)) out.push(...stripsFor(f));
        }
        return out.length ? out : null;
      } catch (e) { return null; }
    }
  }

  // Mount ours as the last child of the dashboard app's scene-graph root (<vsg-app>), after its
  // existing children, so nothing already there moves. (window.Dashboard itself is a MobX observer,
  // whose reactive render can't be wrapped once mounted.)
  let app = null;
  for (const stack = fibers(); stack.length;) {
    const fb = stack.pop();
    if (fb.stateNode && typeof fb.stateNode.toggleDebugPointer === 'function') { app = fb.stateNode; break; }
    if (fb.sibling) stack.push(fb.sibling);
    if (fb.child) stack.push(fb.child);
  }
  if (!app) return 'not patched: dashboard app component not found';
  const hadOwnRender = Object.prototype.hasOwnProperty.call(app, 'render');
  const origRender = app.render;
  app.render = function (...args) {
    const tree = origRender.apply(this, args);
    const kids = tree?.props?.children;
    if (!tree || typeof tree !== 'object' || !Array.isArray(kids)) return tree;
    SAMPLE ??= tree;
    return Object.assign({}, tree, { props: Object.assign({}, tree.props,
      { children: [...kids, el(SftScrollStrips, { key: 'sft-scroll-strips' })] }) });
  };
  try { app.forceUpdate(); } catch (e) {}
  all[NAME] = {
    version: VERSION, stats,
    stop: () => { if (hadOwnRender) app.render = origRender; else delete app.render; try { app.forceUpdate(); } catch (e) {} },
    configChanged: () => {},                                // ours re-renders twice a second anyway
  };
  return 'patched';
})()
