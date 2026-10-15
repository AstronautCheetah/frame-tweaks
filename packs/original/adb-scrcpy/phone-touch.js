// frame-tweaks phone-touch: laser clicks on the Android Mirror window land where you aim.
// The Steam session maps the laser wrongly on a window narrower than its screen (every click on the
// upright phone landed at the window's left edge). So a see-through layer of ours covers the mirror
// window and takes the laser instead: where you press, drag and let go goes to phone-touch (through
// its sftPhoneTouch binding), which sends them to the phone as touches. The layer is there only
// while phone-touch runs (it sets window.__sftPhoneTouchAlive every 2 s). A gear below the window's
// lower-left corner opens its settings beside it (picture, smoothness, joystick speed; saved by
// phone-touch in ~/.config/frame-tweaks/phone.conf, which it hands back as window.__sftPhoneTouchConf).
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// requires: panel anchors | GetPanelAnchorID(
// requires: frame panel height | latestMeasuredPanelLocalHeight
// requires: window.Dashboard | window.Dashboard=
// requires: overlay picture size | GetOverlayMouseScale(
// requires: EDockLocation.Dashboard = 1 | .Dashboard=1]="Dashboard"
// requires: EDockLocation.World = 4 | .World=4]="World"
(() => {
  const NAME = 'phone-touch', VERSION = 15;
  const TITLE = 'Android Mirror';             // the mirror window's title (phone sets it; English, as it's matched)
  const TOP_CENTER = 1, CENTER_LEFT = 3;      // panel anchors
  // Text in the user's language: sft-dashboard sends window.__sftI18n for T(text), N(text).
  const T = (s) => window.__sftI18n?.t?.[s] ?? s, N = (s) => s;
  const LIFT_M = 0.002;                       // the layer floats 2 mm in front of the picture
  const stats = { downs: 0, moves: 0, ups: 0, wheels: 0, lastWheel: null, hovers: 0, leaves: 0, lostUps: 0, trail: [] };
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore, DS = window.DashboardStore, L = window.__sftLib;
  if (!FS || !DS) return 'not patched: dashboard objects missing';
  if (!L) return 'not patched: the dashboard helpers (vr-dashboard/lib.js) are missing';
  const { el } = L, DASH = L.DOCK.Dashboard, WORLD = L.DOCK.World;
  let PANEL = null, XFORM = null;                   // the dashboard's panel / transform (L.components)
  const alive = () => Date.now() - (window.__sftPhoneTouchAlive || 0) < 6000 && typeof window.sftPhoneTouch === 'function';

  const cached = L.memo();                          // the same pieces while nothing changed (L.memo)
  const pictureSize = L.pictureSize;

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
    [N('Picture size (long side, pixels)'), 'PHONE_MAX_SIZE', ['720', '800', '1024', '1280', '1600', '1920'].map((v) => [v, v]), true],
    [N('Bit rate (Mbit/s)'), 'PHONE_BIT_RATE',
     [['1', '1M'], ['1.5', '1500K'], ['2', '2M'], ['3', '3M'], ['4', '4M'], ['6', '6M'], ['8', '8M']], true],
    [N('Frame rate (fps, at most)'), 'PHONE_MAX_FPS', ['30', '60', '72', '80', '90', '96', '108', '120', '144'].map((v) => [v, v]), true],
    [N('Joystick scrolling'), 'PHONE_STICK_SPEED', [[N('Slow'), '8'], [N('Medium'), '15'], [N('Fast'), '25']], false],
  ];
  // A restart (Restart stream, or phone reconnecting) makes a new window, which the dashboard docks
  // or floats somewhere of its own. Where a floating mirror was (and whether its settings were
  // open) is noted as it goes; when a mirror window goes away and a new one comes within 20 s,
  // the new one is put back there. Two places hold a floating window's pose: its floating
  // component's state (what's drawn) and the dock's remembered pose (what it floats to).
  let carry = null;
  const seen = new Map();                       // frameID → { floating, xf, settings }
  const clone = (xf) => (xf ? JSON.parse(JSON.stringify(xf)) : null);
  const snapshot = (f) => {
    const d = f.docking;
    seen.set(f.frameID, { floating: d?.dockLocation === WORLD, settings: settingsOpen.has(f.frameID),
                          xf: clone(d?.m_mapLastRelativeTransformForDockLocation?.get?.(WORLD)) });
  };
  const carryOver = (f) => {                    // (Restart stream: noted now, as the window goes)
    snapshot(f);
    carry = { from: f.frameID, ...seen.get(f.frameID), until: Date.now() + 20000 };
  };
  const mover = (f) => L.walk((fb) => typeof fb.stateNode?.startFloatingWindowMove === 'function' &&
                                     fb.stateNode.props?.frame === f)?.stateNode ?? null;
  const watchMirrors = () => {
    const now = (FS.frames ?? []).filter((g) => g?.title === TITLE && g.docking);
    for (const f of now) if (!carry || f.frameID === carry.from) snapshot(f);
    for (const [id, last] of seen) {
      if (now.some((g) => g.frameID === id)) continue;
      seen.delete(id);                          // (gone: its successor goes where it was)
      if (!carry && last.floating) carry = { from: id, ...last, until: Date.now() + 20000 };
    }
  };
  const placeCarried = () => {
    if (!carry) return;
    if (Date.now() > carry.until) { carry = null; return; }
    const f = (FS.frames ?? []).find((g) => g?.title === TITLE && g.frameID !== carry.from && g.docking);
    if (!f) return;
    const c = carry;
    if (c.settings) settingsOpen.add(f.frameID);
    if (!c.floating || !c.xf) { carry = null; return; }
    try {
      const d = f.docking;
      d.m_mapLastRelativeTransformForDockLocation.set(WORLD, clone(c.xf));
      if (d.dockLocation !== WORLD) {
        // The dashboard's own SetDockLocation: Float grab's wrapper would pick it up in your hand.
        const own = d.__sftOrigSetDock?.orig ?? d.SetDockLocation;
        own.call(d, WORLD);
        return;                                 // (its floating component mounts next: placed then)
      }
      const m = mover(f);
      if (!m?.state?.xfTransform) return;       // (not mounted yet: next tick)
      if (!m.state.sParentDevice) m.setState({ xfTransform: clone(c.xf) });    // (not while held)
      carry = null;
      snapshot(f);
    } catch (e) {
      carry = null;                             // (the dashboard changed: it stays where it came up)
    }
  };
  const DEFAULTS = { PHONE_MAX_SIZE: '1024', PHONE_BIT_RATE: '2M', PHONE_MAX_FPS: '60', PHONE_STICK_SPEED: '15' };
  const settingsOpen = new Set();               // frame IDs whose panel is showing
  let pending = false;                          // a picture change waits for "Restart stream"
  let redraw = () => {};
  const call = (req) => { try { window.sftPhoneTouch(JSON.stringify(req)); } catch (e) {} };
  const hueOf = () => {
    try {
      const h = window.VRSettingsState?.settings?.get('/settings/camera/monochromeTintHue');
      if (typeof h === 'number' && isFinite(h)) return Math.round(((h % 1) + 1) % 1 * 360);
    } catch (e) {}
    return 210;
  };
  // Haptic ticks on the ⚙ and the settings' buttons, as on the dashboard's own (helpers looked up
  // now: lib.js may have been replaced since this patch loaded).
  const buzz = (name) => window.__sftLib?.tick?.(name);
  const tap = () => ({ onMouseEnter: () => buzz('Enter'), onMouseDown: () => buzz('Snap') });
  const GEAR_SVG = 'M19.4 13a7.5 7.5 0 0 0 0-2l2.1-1.6-2-3.5-2.5 1a7.6 7.6 0 0 0-1.7-1L15 3h-4l-.4 2.9a7.6 7.6 0 0 0-1.7 1' +
    'l-2.5-1-2 3.5L6.6 11a7.5 7.5 0 0 0 0 2l-2.1 1.6 2 3.5 2.5-1a7.6 7.6 0 0 0 1.7 1L11 21h4l.4-2.9a7.6 7.6 0 0 0 1.7-1' +
    'l2.5 1 2-3.5zM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z';
  // Under the window's left end; but beside it, level with its bottom, for an upright mirror docked
  // in the dashboard: the dashboard's own buttons under it (Show Keyboard, View in Theater, …)
  // are wider than so narrow a window, and the gear sat on Show Keyboard.
  const gear = (f, k, H, id, beside) => {
    const h = hueOf(), px = 64, size = GEAR_M * k;
    const isOpen = settingsOpen.has(f.frameID);
    const at = beside ? { x: -(GAP_M * k + size / 2), y: -(H / 2 - size / 2) }
                      : { x: size / 2, y: -(H / 2 + GAP_M * k + size / 2) };
    return el(XFORM, { key: `${f.frameID}-sft-gear`, parent_id: id, translation: { ...at, z: LIFT_M * k } },
      el(PANEL, { key: `${f.frameID}-sft-gear-p`, width: size, interactive: true, only_visible_with_laser: false,
        debug_name: 'SftPhoneGear', origin: 4, inputFocusParams: { bCanTakeKeyboardFocus: false } },
        el('div', { style: { width: `${px}px`, height: `${px}px`, borderRadius: '50%', boxSizing: 'border-box',
                             display: 'flex', alignItems: 'center', justifyContent: 'center',
                             background: isOpen ? `hsla(${h}, 45%, 34%, 0.9)` : `hsla(${h}, 18%, 20%, 0.75)`,
                             border: `2px solid hsla(${h}, 60%, 68%, 0.7)` },
                    ...tap(), onClick: () => { isOpen ? settingsOpen.delete(f.frameID) : settingsOpen.add(f.frameID); redraw(); } },
          el('svg', { width: 40, height: 40, viewBox: '0 0 26 24' },
            el('path', { d: GEAR_SVG, fill: `hsl(${h}, 65%, 80%)`, fillRule: 'evenodd' })))));
  };
  const settings = (f, k, id, beside) => {
    const h = hueOf(), conf = window.__sftPhoneTouchConf || {};
    const button = (label, on, onClick, wide) => el('div', { key: label, ...tap(), onClick, style: {
      flex: wide ? '1 1 100%' : '1 0 auto', minWidth: '58px', padding: '11px 6px', margin: '4px', borderRadius: '10px',
      textAlign: 'center', fontSize: '19px', fontWeight: on ? 700 : 500, color: on ? '#fff' : '#d8dee6',
      background: on ? `hsla(${h}, 50%, 38%, 0.95)` : 'rgba(255, 255, 255, 0.08)',
      border: `1px solid ${on ? `hsla(${h}, 60%, 70%, 0.9)` : 'rgba(255, 255, 255, 0.15)'}` } }, T(label));
    const rows = [];
    for (const [title, key, choices, restart] of OPTIONS) {
      rows.push(el('div', { key: `t-${key}`, style: { fontSize: '17px', color: '#9aa6b2', margin: '14px 4px 2px' } }, T(title)));
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
      button(N('Reset to defaults'), false, () => {
        if (isDefault) return;
        if (!streamDefault) pending = true;
        window.__sftPhoneTouchConf = { ...conf, ...DEFAULTS };
        call({ a: 'reset' });
        redraw();
      }),
      button(pending ? N('Restart stream to apply') : N('Restart stream'), pending,
             () => { pending = false; carryOver(f); call({ a: 'restart' }); redraw(); })));
    const pxW = 460;
    return el(XFORM, { key: `${f.frameID}-sft-set`, parent_id: id,
                       // (left of the window; beside: left of the gear, which is beside it)
                       translation: { x: -(GAP_M * k + (beside ? GEAR_M * k + GAP_M * k : 0) + SETTINGS_M * k / 2),
                                      z: LIFT_M * k } },
      el(PANEL, { key: `${f.frameID}-sft-set-p`, width: SETTINGS_M * k, interactive: true, only_visible_with_laser: false,
        debug_name: 'SftPhoneSettings', origin: 4, inputFocusParams: { bCanTakeKeyboardFocus: false } },
        // (zoom: drawn smaller in the shared page, so it fits; it's shown at the same size in VR)
        el('div', { style: { width: `${pxW}px`, boxSizing: 'border-box', padding: '16px 14px', borderRadius: '18px',
                             background: 'rgba(22, 27, 34, 0.94)', border: `1px solid hsla(${h}, 60%, 68%, 0.5)`,
                             color: '#e8ecf0', fontFamily: 'inherit', zoom: 0.62, textAlign: 'left' } },
          el('div', { style: { display: 'flex', alignItems: 'center' } },
            el('div', { style: { flex: '1', fontSize: '24px', fontWeight: 700 } }, T('Android Mirror')),
            el('div', { ...tap(), onClick: () => { settingsOpen.delete(f.frameID); redraw(); },
                        style: { fontSize: '28px', padding: '0 10px', color: '#9aa6b2' } }, '✕')),
          ...rows,
          el('div', { style: { fontSize: '15px', color: '#9aa6b2', margin: '10px 4px 0' } },
             T('Picture and smoothness apply when the stream restarts; joystick speed at once.')))));
  };
  const buildExtras = (f) => {
    const page = f.activePage, sz = page?.size;
    const H = sz?.latestMeasuredPanelLocalHeight, Hw = sz?.latestMeasuredPanelWorldHeight;
    const id = typeof page?.GetPanelAnchorID === 'function' && page.GetPanelAnchorID(CENTER_LEFT);
    if (!H || !Hw || !id) return [];
    const k = H / Hw, c = pictureSize(page);
    const beside = f.docking?.dockLocation === DASH && c && c.w < c.h;      // upright, docked
    return [gear(f, k, H, id, beside), settingsOpen.has(f.frameID) ? settings(f, k, id, beside) : null];
  };

  const sizes = (f) => {
    const sz = f.activePage?.size, c = f.activePage && pictureSize(f.activePage);
    return [f.frameID, sz?.latestMeasuredPanelLocalHeight, sz?.latestMeasuredPanelWorldHeight, c?.w, c?.h,
            f.curvature?.shouldCurve ? f.curvature.curvatureTransformOriginID : null,
            f.activePage?.GetPanelAnchorID?.(TOP_CENTER) ?? null];
  };
  const layer = (f) => cached(JSON.stringify(['layer', ...sizes(f)]), () => buildLayer(f));
  const extras = (f) => cached(JSON.stringify(['extras', window.__sftI18n?.lang ?? null, ...sizes(f), f.docking?.dockLocation,
                                               settingsOpen.has(f.frameID), pending, hueOf(),
                                               window.__sftPhoneTouchConf ?? null]), () => buildExtras(f));

  // Drawn as the last child of the dashboard app, in the page's bottom-right corner (L.mount; the
  // scroll strips have the left), four times a second.
  const render = () => {
    const c = L.components();
    if (!alive() || !c) return null;
    ({ PANEL, XFORM } = c);
    const out = [];
    for (const f of FS.frames ?? []) {
      if (f?.title !== TITLE) continue;
      const dock = f.docking?.dockLocation;
      if (dock === WORLD || (dock === DASH && f === DS.activeFrame && DS.isFullyVisible)) out.push(layer(f), ...extras(f));
    }
    return out;
  };
  const mounted = L.mount('sft-phone-touch', render, 'right', 250);
  if (!mounted) return 'not patched: dashboard app component not found';
  redraw = mounted.redraw;
  const carryTimer = setInterval(() => { try { watchMirrors(); placeCarried(); } catch (e) {} }, 250);
  all[NAME] = {
    version: VERSION, stats,
    stop: () => {
      mounted.stop();
      clearInterval(carryTimer);
      onUp({ clientX: 0, clientY: 0 });
    },
  };
  return 'patched';
})()
