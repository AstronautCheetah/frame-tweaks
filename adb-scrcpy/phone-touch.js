// frame-tweaks phone-touch: laser clicks on the Android Mirror window land where you aim.
// The Steam session maps the laser wrongly on a window narrower than its screen (every click on the
// upright phone landed at the window's left edge). So a see-through layer of ours covers the mirror
// window and takes the laser instead: where you press, drag and let go goes to phone-touch (through
// its sftPhoneTouch binding), which sends them to the phone as touches. The layer is there only
// while phone-touch runs (it sets window.__sftPhoneTouchAlive every 2 s). A gear below the window's
// lower-left corner opens its settings beside it (picture, smoothness, joystick speed; saved by
// phone-touch in ~/.config/phone.conf, which it hands back as window.__sftPhoneTouchConf).
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// requires: panel anchors | GetPanelAnchorID(
// requires: frame panel height | latestMeasuredPanelLocalHeight
// requires: window.Dashboard | window.Dashboard=
// requires: overlay picture size | GetOverlayMouseScale(
// requires: EDockLocation.Dashboard = 1 | .Dashboard=1]="Dashboard"
// requires: EDockLocation.World = 4 | .World=4]="World"
(() => {
  const NAME = 'phone-touch', VERSION = 9, DASH = 1, WORLD = 4;
  const TITLE = 'Android Mirror';             // the mirror window's title (phone sets it)
  const TOP_CENTER = 1, CENTER_LEFT = 3;      // panel anchors
  const LIFT_M = 0.002;                       // the layer floats 2 mm in front of the picture
  const stats = { downs: 0, moves: 0, ups: 0, wheels: 0, lastWheel: null, hovers: 0, leaves: 0, lostUps: 0, trail: [] };
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
  // The same pieces while nothing they show has changed: the dashboard redraws often (each time
  // the laser crosses one of SteamVR's buttons), and fresh pieces, even identical ones, make it
  // send them to SteamVR again, which showed as jitter.
  const memo = new Map();
  const cached = (key, make) => {
    if (memo.has(key)) return memo.get(key);
    const v = make();
    memo.set(key, v);
    if (memo.size > 40) memo.delete(memo.keys().next().value);
    return v;
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
    // No button held: the let-go went missing (it happens with the laser). End the touch there,
    // or the joystick, which waits for the touch to end, would stay off.
    if (ev.buttons === 0) { stats.lostUps++; return onUp(ev); }
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
  const mark = (what) => { stats.trail.push([what, Date.now() % 1e6]); if (stats.trail.length > 60) stats.trail.shift(); };
  const onHover = (ev, size) => {
    if (touch && ev.buttons === 0) { stats.lostUps++; onUp(ev); }
    if (touch || Date.now() - lastHover < 100) return;
    if (!lastHover) mark('hover');
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
    mark('leave');
    lastHover = 0;
    try { window.sftPhoneTouch(JSON.stringify({ a: 'leave' })); } catch (e) {}
  };
  const buildLayer = (f) => {
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
            mark('down');
            if (touch) onUp(ev);                    // a new press ends a touch whose let-go went missing
            touch = { rect: ev.currentTarget.getBoundingClientRect(), size: c };
            send('down', ev);
            window.addEventListener('mousemove', onMove, true);
            window.addEventListener('mouseup', onUp, true);
            window.addEventListener('pointerup', onUp, true);
          } })));
  };

  // ---- the gear and its settings panel ----
  const GEAR_M = 0.045, GAP_M = 0.015, SETTINGS_M = 0.34;       // sizes, metres
  // [title, key, [[label, value]...], needs a stream restart]: the real settings (scrcpy's
  // --max-size, --video-bit-rate, --max-fps); frame rates are the Steam Frame's refresh rates.
  const OPTIONS = [
    ['Picture size (long side, pixels)', 'PHONE_MAX_SIZE', ['720', '800', '1024', '1280', '1600', '1920'].map((v) => [v, v]), true],
    ['Bit rate (Mbit/s)', 'PHONE_BIT_RATE',
     [['1', '1M'], ['1.5', '1500K'], ['2', '2M'], ['3', '3M'], ['4', '4M'], ['6', '6M'], ['8', '8M']], true],
    ['Frame rate (fps, at most)', 'PHONE_MAX_FPS', ['30', '60', '72', '80', '90', '96', '108', '120', '144'].map((v) => [v, v]), true],
    ['Joystick scrolling', 'PHONE_STICK_SPEED', [['Slow', '8'], ['Medium', '15'], ['Fast', '25']], false],
  ];
  // A restart makes a new window, which the dashboard would dock. Carry the floating one's place
  // (and its open settings) over to the new mirror window when it appears (within 20 s).
  let carry = null;
  const carryOver = (f) => {
    const d = f.docking;
    const xf = d?.m_mapLastRelativeTransformForDockLocation?.get?.(WORLD);
    carry = { from: f.frameID, floating: d?.dockLocation === WORLD, xf, settings: settingsOpen.has(f.frameID),
              until: Date.now() + 20000 };
  };
  const placeCarried = () => {
    if (!carry) return;
    if (Date.now() > carry.until) { carry = null; return; }
    const f = (FS.frames ?? []).find((g) => g?.title === TITLE && g.frameID !== carry.from && g.docking);
    if (!f) return;
    const c = carry; carry = null;
    if (c.settings) settingsOpen.add(f.frameID);
    if (!c.floating || f.docking.dockLocation === WORLD) return;
    try {
      if (c.xf) f.docking.m_mapLastRelativeTransformForDockLocation.set(WORLD, c.xf);
      // The dashboard's own SetDockLocation: Float grab's wrapper would pick it up in your hand.
      const own = f.docking.__sftOrigSetDock?.orig ?? f.docking.SetDockLocation;
      own.call(f.docking, WORLD);
    } catch (e) { /* the dashboard changed: it stays docked */ }
  };
  const DEFAULTS = { PHONE_MAX_SIZE: '1024', PHONE_BIT_RATE: '2M', PHONE_MAX_FPS: '60', PHONE_STICK_SPEED: '15' };
  const settingsOpen = new Set();               // frame IDs whose panel is showing
  let pending = false;                          // a picture change waits for "Restart stream"
  let inst = null;
  const redraw = () => { try { inst?.forceUpdate(); } catch (e) {} };
  const call = (req) => { try { window.sftPhoneTouch(JSON.stringify(req)); } catch (e) {} };
  const hueOf = () => {
    try {
      const h = window.VRSettingsState?.settings?.get('/settings/camera/monochromeTintHue');
      if (typeof h === 'number' && isFinite(h)) return Math.round(((h % 1) + 1) % 1 * 360);
    } catch (e) {}
    return 210;
  };
  const GEAR_SVG = 'M19.4 13a7.5 7.5 0 0 0 0-2l2.1-1.6-2-3.5-2.5 1a7.6 7.6 0 0 0-1.7-1L15 3h-4l-.4 2.9a7.6 7.6 0 0 0-1.7 1' +
    'l-2.5-1-2 3.5L6.6 11a7.5 7.5 0 0 0 0 2l-2.1 1.6 2 3.5 2.5-1a7.6 7.6 0 0 0 1.7 1L11 21h4l.4-2.9a7.6 7.6 0 0 0 1.7-1' +
    'l2.5 1 2-3.5zM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z';
  const gear = (f, k, H, id) => {
    const h = hueOf(), px = 64, size = GEAR_M * k;
    const isOpen = settingsOpen.has(f.frameID);
    return el(XFORM, { key: `${f.frameID}-sft-gear`, parent_id: id,
                       translation: { x: size / 2, y: -(H / 2 + GAP_M * k + size / 2), z: LIFT_M * k } },
      el(PANEL, { key: `${f.frameID}-sft-gear-p`, width: size, interactive: true, only_visible_with_laser: false,
        debug_name: 'SftPhoneGear', origin: 4, inputFocusParams: { bCanTakeKeyboardFocus: false } },
        el('div', { style: { width: `${px}px`, height: `${px}px`, borderRadius: '50%', boxSizing: 'border-box',
                             display: 'flex', alignItems: 'center', justifyContent: 'center',
                             background: isOpen ? `hsla(${h}, 45%, 34%, 0.9)` : `hsla(${h}, 18%, 20%, 0.75)`,
                             border: `2px solid hsla(${h}, 60%, 68%, 0.7)` },
                    onClick: () => { isOpen ? settingsOpen.delete(f.frameID) : settingsOpen.add(f.frameID); redraw(); } },
          el('svg', { width: 40, height: 40, viewBox: '0 0 26 24' },
            el('path', { d: GEAR_SVG, fill: `hsl(${h}, 65%, 80%)`, fillRule: 'evenodd' })))));
  };
  const settings = (f, k, id) => {
    const h = hueOf(), conf = window.__sftPhoneTouchConf || {};
    const button = (label, on, onClick, wide) => el('div', { key: label, onClick, style: {
      flex: wide ? '1 1 100%' : '1 0 auto', minWidth: '58px', padding: '11px 6px', margin: '4px', borderRadius: '10px',
      textAlign: 'center', fontSize: '19px', fontWeight: on ? 700 : 500, color: on ? '#fff' : '#d8dee6',
      background: on ? `hsla(${h}, 50%, 38%, 0.95)` : 'rgba(255, 255, 255, 0.08)',
      border: `1px solid ${on ? `hsla(${h}, 60%, 70%, 0.9)` : 'rgba(255, 255, 255, 0.15)'}` } }, label);
    const rows = [];
    for (const [title, key, choices, restart] of OPTIONS) {
      rows.push(el('div', { key: `t-${key}`, style: { fontSize: '17px', color: '#9aa6b2', margin: '14px 4px 2px' } }, title));
      rows.push(el('div', { key: `r-${key}`, style: { display: 'flex', flexWrap: 'wrap' } },
        ...choices.map(([label, value]) => button(label, conf[key] === value, () => {
          if (conf[key] === value) return;
          window.__sftPhoneTouchConf = { ...conf, [key]: value };    // shown at once; phone-touch confirms
          if (restart) pending = true;
          call({ a: 'set', conf: { [key]: value } });
          redraw();
        }))));
    }
    // Back to the defaults (phone-touch's DEFAULTS; kept in step by tests/test_phone_touch.py).
    const isDefault = Object.entries(DEFAULTS).every(([key, v]) => conf[key] === v);
    const streamDefault = OPTIONS.every(([, key, , restart]) => !restart || conf[key] === DEFAULTS[key]);
    rows.push(el('div', { key: 'restart', style: { display: 'flex', marginTop: '14px' } },
      button('Reset to defaults', false, () => {
        if (isDefault) return;
        if (!streamDefault) pending = true;
        window.__sftPhoneTouchConf = { ...conf, ...DEFAULTS };
        call({ a: 'reset' });
        redraw();
      }),
      button(pending ? 'Restart stream to apply' : 'Restart stream', pending,
             () => { pending = false; carryOver(f); call({ a: 'restart' }); redraw(); })));
    const pxW = 460;
    return el(XFORM, { key: `${f.frameID}-sft-set`, parent_id: id,
                       translation: { x: -(GAP_M * k + SETTINGS_M * k / 2), z: LIFT_M * k } },
      el(PANEL, { key: `${f.frameID}-sft-set-p`, width: SETTINGS_M * k, interactive: true, only_visible_with_laser: false,
        debug_name: 'SftPhoneSettings', origin: 4, inputFocusParams: { bCanTakeKeyboardFocus: false } },
        // (zoom: drawn smaller in the shared page, so it fits; it's shown at the same size in VR)
        el('div', { style: { width: `${pxW}px`, boxSizing: 'border-box', padding: '16px 14px', borderRadius: '18px',
                             background: 'rgba(22, 27, 34, 0.94)', border: `1px solid hsla(${h}, 60%, 68%, 0.5)`,
                             color: '#e8ecf0', fontFamily: 'inherit', zoom: 0.62, textAlign: 'left' } },
          el('div', { style: { display: 'flex', alignItems: 'center' } },
            el('div', { style: { flex: '1', fontSize: '24px', fontWeight: 700 } }, 'Android Mirror'),
            el('div', { onClick: () => { settingsOpen.delete(f.frameID); redraw(); },
                        style: { fontSize: '28px', padding: '0 10px', color: '#9aa6b2' } }, '✕')),
          ...rows,
          el('div', { style: { fontSize: '15px', color: '#9aa6b2', margin: '10px 4px 0' } },
             'Picture and smoothness apply when the stream restarts; joystick speed at once.'))));
  };
  const buildExtras = (f) => {
    const page = f.activePage, sz = page?.size;
    const H = sz?.latestMeasuredPanelLocalHeight, Hw = sz?.latestMeasuredPanelWorldHeight;
    const id = typeof page?.GetPanelAnchorID === 'function' && page.GetPanelAnchorID(CENTER_LEFT);
    if (!H || !Hw || !id) return [];
    const k = H / Hw;
    return [gear(f, k, H, id), settingsOpen.has(f.frameID) ? settings(f, k, id) : null];
  };

  const sizes = (f) => {
    const sz = f.activePage?.size, c = f.activePage && pictureSize(f.activePage);
    return [f.frameID, sz?.latestMeasuredPanelLocalHeight, sz?.latestMeasuredPanelWorldHeight, c?.w, c?.h,
            f.curvature?.shouldCurve ? f.curvature.curvatureTransformOriginID : null,
            f.activePage?.GetPanelAnchorID?.(TOP_CENTER) ?? null];
  };
  const layer = (f) => cached(JSON.stringify(['layer', ...sizes(f)]), () => buildLayer(f));
  const extras = (f) => cached(JSON.stringify(['extras', ...sizes(f), settingsOpen.has(f.frameID), pending, hueOf(),
                                               window.__sftPhoneTouchConf ?? null]), () => buildExtras(f));

  const AREA = { position: 'absolute', right: '0px', bottom: '0px', width: '920px', textAlign: 'right' };

  class SftPhoneTouch extends Base {
    componentDidMount() {
      mounted++; inst = this;
      this.timer = setInterval(() => { try { placeCarried(); this.forceUpdate(); } catch (e) {} }, 250);
    }
    componentWillUnmount() { mounted--; if (inst === this) inst = null; clearInterval(this.timer); }
    render() {
      try {
        if (!alive() || !learn()) return null;
        const out = [];
        for (const f of FS.frames ?? []) {
          if (f?.title !== TITLE) continue;
          const dock = f.docking?.dockLocation;
          if (dock === WORLD || (dock === DASH && f === DS.activeFrame && DS.isFullyVisible)) out.push(layer(f), ...extras(f));
        }
        const parts = out.filter(Boolean);
        // Our pieces are drawn from one shared page (1860 x 2048). Placed after the dashboard's
        // own content, they moved whenever it changed size (its buttons grow under the laser),
        // which showed as jitter, and a tall settings panel ran off the page's bottom. So they
        // sit in a fixed corner of their own: the bottom right (the scroll strips have the left).
        return parts.length ? el('div', { key: 'sft-phone-touch-area', style: AREA }, ...parts) : null;
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
