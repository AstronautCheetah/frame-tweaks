// steam-frame-tweaks phone-touch: laser clicks on the Android Mirror window land where you aim.
// The Steam session maps the laser wrongly on a window narrower than its screen (every click on the
// upright phone landed at the window's left edge). So a see-through layer of ours covers the mirror
// window and takes the laser instead: where you press, drag and let go goes to phone-touch (through
// its sftPhoneTouch binding), which sends them to the phone as touches. The layer is there only
// while phone-touch runs (it sets window.__sftPhoneTouchAlive every 2 s).
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// requires: panel anchors | GetPanelAnchorID(e){
// requires: frame panel height | latestMeasuredPanelLocalHeight
// requires: window.Dashboard | window.Dashboard=
// requires: overlay picture size | GetOverlayMouseScale(
// requires: EDockLocation.Dashboard = 1 | e[e.Dashboard=1]="Dashboard"
// requires: EDockLocation.World = 4 | e[e.World=4]="World"
(() => {
  const NAME = 'phone-touch', VERSION = 3, DASH = 1, WORLD = 4;
  const TITLE = 'Android Mirror';             // the mirror window's title (phone sets it)
  const TOP_CENTER = 1;                       // panel anchor
  const LIFT_M = 0.002;                       // the layer floats 2 mm in front of the picture
  const stats = { downs: 0, moves: 0, ups: 0, wheels: 0, lastWheel: null, hovers: 0, leaves: 0 };
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore, DS = window.DashboardStore, D = window.Dashboard;
  if (!FS || !DS || !D) return 'not patched: dashboard objects missing';
  const Base = Object.getPrototypeOf(D.constructor);
  if (!Base?.prototype?.isReactComponent) return 'not patched: no React component class';
  const alive = () => Date.now() - (window.__sftPhoneTouchAlive || 0) < 6000 && typeof window.sftPhoneTouch === 'function';

  // The dashboard's panel and transform components, found among its rendered fibers (as in scroll-strips).
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
  const pictureSize = (page) => {
    try {
      const m = VRHTML.VROverlay.GetOverlayMouseScale(VRHTML.VROverlay.FindOverlay(page.summonOverlayKey));
      if (m?.x > 0 && m?.y > 0) return { w: m.x, h: m.y };
    } catch (e) { /* no overlay */ }
  };

  // A press, then drags, then a let-go: one finger on the phone.
  let touch = null;
  const send = (a, ev) => {
    const t = touch, r = t.rect;
    try {
      window.sftPhoneTouch(JSON.stringify({ a, u: (ev.clientX - r.left) / r.width, v: (ev.clientY - r.top) / r.height,
                                            w: t.size.w, h: t.size.h }));
    } catch (e) {}
  };
  const onMove = (ev) => {
    if (!touch) return;
    stats.moves++;
    send('move', ev);
  };
  const onUp = (ev) => {
    window.removeEventListener('mousemove', onMove, true);
    window.removeEventListener('mouseup', onUp, true);
    window.removeEventListener('pointerup', onUp, true);
    if (!touch) return;
    stats.ups++;
    send('up', ev);
    touch = null;
  };
  // The joystick scrolls the window under the laser: here, our layer. Pass it on as the phone's
  // scroll wheel, in notches (a wheel notch is 100 page pixels here, or 1 line or page).
  const onWheel = (ev, size) => {
    stats.wheels++;
    stats.lastWheel = [ev.deltaMode, ev.deltaX, ev.deltaY];
    const notch = ev.deltaMode === 0 ? 100 : 1, r = ev.currentTarget.getBoundingClientRect();
    try {
      window.sftPhoneTouch(JSON.stringify({ a: 'scroll', u: (ev.clientX - r.left) / r.width, v: (ev.clientY - r.top) / r.height,
                                            dx: ev.deltaX / notch, dy: ev.deltaY / notch, w: size.w, h: size.h }));
    } catch (e) {}
  };
  // Where the laser rests (no press): phone-touch scrolls there with the joystick, which SteamVR
  // doesn't pass to the layer. At most 10 a second; and when it leaves.
  let lastHover = 0;
  const onHover = (ev, size) => {
    if (touch || Date.now() - lastHover < 100) return;
    lastHover = Date.now();
    stats.hovers++;
    const r = ev.currentTarget.getBoundingClientRect();
    try {
      window.sftPhoneTouch(JSON.stringify({ a: 'hover', u: (ev.clientX - r.left) / r.width, v: (ev.clientY - r.top) / r.height,
                                            w: size.w, h: size.h }));
    } catch (e) {}
  };
  const onLeave = () => {
    stats.leaves++;
    lastHover = 0;
    try { window.sftPhoneTouch(JSON.stringify({ a: 'leave' })); } catch (e) {}
  };
  const layer = (f) => {
    const page = f.activePage, sz = page?.size;
    const H = sz?.latestMeasuredPanelLocalHeight, Hw = sz?.latestMeasuredPanelWorldHeight, c = page && pictureSize(page);
    const id = c && typeof page.GetPanelAnchorID === 'function' && page.GetPanelAnchorID(TOP_CENTER);
    if (!H || !Hw || !id) return null;
    const W = H * c.w / c.h, k = H / Hw;
    // A curved window: bend the layer around the same origin, so it stays on the picture.
    const curveId = f.curvature?.shouldCurve ? f.curvature.curvatureTransformOriginID : undefined;
    const pxW = 240, pxH = Math.round(pxW * c.h / c.w);         // small page element, same shape
    return el(XFORM, { key: `${f.frameID}-sft-touch`, parent_id: id, translation: { y: -H / 2, z: LIFT_M * k } },
      el(PANEL, { key: `${f.frameID}-sft-touch-p`, width: W, interactive: true, only_visible_with_laser: false,
        debug_name: 'SftPhoneTouch', origin: 4, inputFocusParams: { bCanTakeKeyboardFocus: false },
        ...(curveId ? { curvature_origin_id: curveId } : {}) },
        el('div', { style: { width: `${pxW}px`, height: `${pxH}px`, background: 'rgba(0, 0, 0, 0)' },
          onWheel: (ev) => onWheel(ev, c),
          onMouseMove: (ev) => onHover(ev, c),
          onMouseLeave: onLeave,
          onMouseDown: (ev) => {
            stats.downs++;
            if (touch) onUp(ev);                    // a new press ends a touch whose let-go went missing
            touch = { rect: ev.currentTarget.getBoundingClientRect(), size: c };
            send('down', ev);
            window.addEventListener('mousemove', onMove, true);
            window.addEventListener('mouseup', onUp, true);
            window.addEventListener('pointerup', onUp, true);
          } })));
  };

  class SftPhoneTouch extends Base {
    componentDidMount() { mounted++; this.timer = setInterval(() => { try { this.forceUpdate(); } catch (e) {} }, 500); }
    componentWillUnmount() { mounted--; clearInterval(this.timer); }
    render() {
      try {
        if (!alive() || !learn()) return null;
        const out = [];
        for (const f of FS.frames ?? []) {
          if (f?.title !== TITLE) continue;
          const dock = f.docking?.dockLocation;
          if (dock === WORLD || (dock === DASH && f === DS.activeFrame && DS.isFullyVisible)) out.push(layer(f));
        }
        return out.filter(Boolean).length ? out.filter(Boolean) : null;
      } catch (e) { return null; }
    }
  }

  // Mounted after the dashboard app's own children, like scroll-strips. Another patch that
  // restores the app's render when it stops would drop ours: put it back if so.
  let app = null;
  for (const stack = fibers(); stack.length;) {
    const fb = stack.pop();
    if (fb.stateNode && typeof fb.stateNode.toggleDebugPointer === 'function') { app = fb.stateNode; break; }
    if (fb.sibling) stack.push(fb.sibling);
    if (fb.child) stack.push(fb.child);
  }
  if (!app) return 'not patched: dashboard app component not found';
  let on = true, mounted = 0;
  const mount = () => {
    const below = app.render;
    app.render = function (...args) {
      const tree = below.apply(this, args);
      const kids = tree?.props?.children;
      if (!on || !tree || typeof tree !== 'object' || !Array.isArray(kids)) return tree;
      SAMPLE ??= tree;
      return Object.assign({}, tree, { props: Object.assign({}, tree.props,
        { children: [...kids, el(SftPhoneTouch, { key: 'sft-phone-touch' })] }) });
    };
    try { app.forceUpdate(); } catch (e) {}
  };
  mount();
  const guard = setInterval(() => { if (on && !mounted) mount(); }, 2000);
  all[NAME] = {
    version: VERSION, stats,
    stop: () => {
      on = false;                                  // stays in the chain, passing straight through
      clearInterval(guard);
      onUp({ clientX: 0, clientY: 0 });
      try { app.forceUpdate(); } catch (e) {}
    },
  };
  return 'patched';
})()
