// steam-frame-tweaks scroll-strips: big scroll strips beside each window (the one docked in the
// dashboard and every floating one), easy to hit with the laser. Each works like a joystick: press,
// then drag away from where you pressed to scroll (the farther, the faster; back past it reverses);
// let go to stop. A quick tap near an end pages. Scrolling goes to the window you last clicked, as
// arrow keys / PgUp-PgDn through vr-dashboard's sftScroll binding (in VR, the Steam session takes
// pointer input only from the lasers, so a mouse wheel can't be injected; keys can). The Android
// Mirror is scrolled through its phone-touch helper instead (see adb-scrcpy).
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard. Settings:
// window.__sftPatchConfig["scroll-strips"] = {vertical: "right"|"left"|"off",
//   horizontal: "top"|"bottom"|"off", thickness: metres, gap: metres, back: metres}. Sizes are real metres (the
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
  const NAME = 'scroll-strips', VERSION = 15, DASH = 1, WORLD = 4;
  const ANCHOR = { CenterLeft: 3, CenterRight: 5, TopCenter: 1, BottomCenter: 7, Center: 4 };
  const MAX_RATE = 30;               // scroll steps per second at the strip's end
  const DEAD_ZONE = 0.08;            // around the centre (fraction of half the strip): no scrolling
  const TICK_MS = 50, TAP_MS = 300, HOLD_STILL_MS = 3000;
  // Colours follow SteamVR's Camera Color Tint (/settings/camera/monochromeTintHue, 0..1; blue
  // when it can't be read), unless the settings (the gear) pick a hue of their own (color: 0..1).
  const tintHue = () => {
    try {
      const h = window.VRSettingsState?.settings?.get('/settings/camera/monochromeTintHue');
      if (typeof h === 'number' && isFinite(h)) return ((h % 1) + 1) % 1 * 360;
    } catch (e) {}
    return 210;
  };
  const hue = () => {
    const c = window.__sftPatchConfig?.[NAME]?.color;
    return typeof c === 'number' && isFinite(c) ? ((c % 1) + 1) % 1 * 360 : tintHue();
  };
  const colors = () => {
    const h = Math.round(hue());
    return { idle: `hsla(${h}, 18%, 20%, 0.6)`, active: `hsla(${h}, 45%, 34%, 0.85)`,
             border: `hsla(${h}, 60%, 68%, 0.65)`, knob: `hsl(${h}, 65%, 68%)`, origin: 'rgba(232, 236, 240, 0.35)' };
  };
  const PAGE = 10;                   // notches for a tap near an end
  const stats = { downs: 0, moves: 0, ups: 0, sent: 0, noBinding: 0 };   // for diagnosis
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore, DS = window.DashboardStore, D = window.Dashboard;
  if (!FS || !DS || !D) return 'not patched: dashboard objects missing';
  const Base = Object.getPrototypeOf(D.constructor);
  if (!Base?.prototype?.isReactComponent) return 'not patched: no React component class';
  const cfg = () => {
    const c = { vertical: 'right', horizontal: 'top', thickness: 0.04, gap: 0.015, back: 0.03, ...(window.__sftPatchConfig?.[NAME] ?? {}) };
    c.thickness = Math.min(0.1, Math.max(0.015, Number(c.thickness) || 0.04));
    c.gap = Math.min(0.1, Math.max(0, Number(c.gap) || 0.015));
    // Set back a little behind the window's plane, so SteamVR's own buttons by the window's edge
    // (e.g. Enter Gamepad Mode above it) draw in front instead of through the strip.
    c.back = Math.min(0.2, Math.max(0, Number(c.back ?? 0.03) || 0));
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

  // A strip works like a joystick: press to set a centre, drag away from it to scroll (the farther,
  // the faster; back across the centre reverses), let go to stop. A quick tap near an end pages.
  let drag = null;
  const send = (target, dx, dy, page = 0) => {
    // The Android Mirror (with phone-touch running): scroll the phone itself, as its wheel. Keys
    // would go to the window the Steam session last saw clicked, and clicks on the mirror go to
    // phone-touch's layer instead, so that was the dashboard's window. A page is 10 notches.
    if (typeof target === 'object') {
      try {
        window.sftPhoneTouch(JSON.stringify({ a: 'scroll', u: 0.5, v: 0.5, w: target.w, h: target.h,
                                              dx: dx + 0, dy: -dy - page * 10 }));
        stats.sent++;
      } catch (e) {}
      return;
    }
    if (typeof window.sftScroll !== 'function') { stats.noBinding++; return; }
    try { window.sftScroll(JSON.stringify({ target, dx, dy, page })); stats.sent++; } catch (e) {}
  };
  const tick = () => {                        // while held: scroll at the rate the offset asks for
    const d = drag;
    if (!d) return;
    if (Date.now() - d.lastMove > HOLD_STILL_MS) return onUp();      // the release went missing
    const u = Math.max(-1, Math.min(1, d.offset / (d.length / 2)));   // -1..1 from the centre
    const mag = Math.max(0, (Math.abs(u) - DEAD_ZONE) / (1 - DEAD_ZONE));
    d.carry += Math.sign(u) * MAX_RATE * mag ** 1.6 * (TICK_MS / 1000);
    const steps = Math.trunc(d.carry);
    if (steps) {
      d.carry -= steps;
      // Drag down (or right) scrolls down (or right); the service's +dy is up.
      d.axis === 'y' ? send(d.target, 0, -steps) : send(d.target, steps, 0);
    }
  };
  const onMove = (ev) => {
    if (!drag) return;
    stats.moves++;
    drag.lastMove = Date.now();
    const pos = drag.axis === 'y' ? ev.clientY : ev.clientX;
    drag.offset = pos - drag.start;
    drag.moved = Math.max(drag.moved, Math.abs(drag.offset));
    if (drag.knob) drag.knob.style[drag.axis === 'y' ? 'top' : 'left'] = `${pos - drag.from}px`;
  };
  const onUp = () => {
    stats.ups++;
    window.removeEventListener('mousemove', onMove, true);
    window.removeEventListener('mouseup', onUp, true);
    window.removeEventListener('pointerup', onUp, true);
    const d = drag; drag = null;
    if (!d) return;
    clearInterval(d.timer);
    d.knob?.remove(); d.origin?.remove();
    if (d.el) d.el.style.background = colors().idle;
    if (Date.now() - d.t0 > TAP_MS || d.moved > d.length * 0.03) return;
    const at = (d.start - d.from) / d.length;                    // a quick tap near an end: a page
    if (at < 0.25) d.axis === 'y' ? send(d.target, 0, 0, 1) : send(d.target, -PAGE, 0);
    else if (at > 0.75) d.axis === 'y' ? send(d.target, 0, 0, -1) : send(d.target, PAGE, 0);
  };
  const dot = (el, axis, at, color, size) => {               // a marker on the strip (plain DOM)
    const m = document.createElement('div');
    Object.assign(m.style, { position: 'absolute', width: `${size}px`, height: `${size}px`, borderRadius: '50%',
      background: color, pointerEvents: 'none', transform: 'translate(-50%, -50%)',
      [axis === 'y' ? 'top' : 'left']: `${at}px`, [axis === 'y' ? 'left' : 'top']: '50%' });
    el.appendChild(m);
    return m;
  };
  const strip = (key, axis, length, thick, target, curveId) => {   // sizes in the anchor's units
    const px = 16, lenPx = Math.min(600, Math.round(px * length / thick));   // small page elements
    const style = { width: `${axis === 'y' ? px : lenPx}px`, height: `${axis === 'y' ? lenPx : px}px`,
      background: colors().idle, position: 'relative', borderRadius: `${px / 2}px`, boxSizing: 'border-box',
      border: `1px solid ${colors().border}` };
    return el(PANEL, { key, width: axis === 'y' ? thick : length, interactive: true, only_visible_with_laser: false,
      debug_name: `SftScroll${axis.toUpperCase()}`, origin: ANCHOR.Center, inputFocusParams: { bCanTakeKeyboardFocus: false },
      ...(curveId ? { curvature_origin_id: curveId } : {}) },
      el('div', { style, onMouseDown: (ev) => {
        stats.downs++;
        if (drag) onUp();                         // a new press ends any drag still open
        const el = ev.currentTarget, r = el.getBoundingClientRect();
        const start = axis === 'y' ? ev.clientY : ev.clientX, from = axis === 'y' ? r.top : r.left;
        el.style.background = colors().active;
        drag = { axis, target, el, start, from, length: axis === 'y' ? r.height : r.width, offset: 0, moved: 0,
                 carry: 0, t0: Date.now(), lastMove: Date.now(),
                 origin: dot(el, axis, start - from, colors().origin, 10),
                 knob: dot(el, axis, start - from, colors().knob, 14) };
        drag.timer = setInterval(tick, TICK_MS);
        window.addEventListener('mousemove', onMove, true);
        window.addEventListener('mouseup', onUp, true);
        window.addEventListener('pointerup', onUp, true);
      } }));
  };
  // The window's picture size, from its overlay: the page's latestContentSize is only read again
  // when something else changes, so after a phone mirror turned it kept the old shape (strips the
  // wrong length).
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
      if (m?.x > 0 && m?.y > 0) return { unWidth: m.x, unHeight: m.y };
    } catch (e) { /* no overlay */ }
    return page?.size?.latestContentSize;
  };
  const buildStrips = (f) => {
    const page = f?.activePage, sz = page?.size;
    const H = sz?.latestMeasuredPanelLocalHeight, Hw = sz?.latestMeasuredPanelWorldHeight, c = page && pictureSize(page);
    if (!H || !Hw || !c?.unHeight || typeof page.GetPanelAnchorID !== 'function') return [];
    const o = cfg(), k = H / Hw;                 // anchor units per metre (the panel's own scale)
    // The desktop scrolls through its own portal; other windows get keys (see vr-dashboard).
    const phone = f.title === 'Android Mirror' && typeof window.sftPhoneTouch === 'function' &&
      Date.now() - (window.__sftPhoneTouchAlive || 0) < 6000;
    const target = phone ? { w: c.unWidth, h: c.unHeight }
      : /^KDE Wayland Compositor/.test(f.title ?? '') ? 'desktop' : 'window';
    // A curved window: bend the horizontal strip around the same origin as the window.
    const curveId = f.curvature?.shouldCurve ? f.curvature.curvatureTransformOriginID : undefined;
    const W = H * c.unWidth / c.unHeight, t = o.thickness * k, g = o.gap * k, z = -o.back * k, out = [];
    const at = (anchor, translation, child) => {
      const id = page.GetPanelAnchorID(anchor);
      return id ? el(XFORM, { key: `${f.frameID}-${anchor}`, parent_id: id, translation }, child) : null;
    };
    if (o.vertical !== 'off') {
      const left = o.vertical === 'left';
      out.push(at(left ? ANCHOR.CenterLeft : ANCHOR.CenterRight, { x: (left ? -1 : 1) * (g + t / 2), z },
                  strip(`${f.frameID}-y`, 'y', H, t, target)));
    }
    if (o.horizontal !== 'off') {
      const bottom = o.horizontal === 'bottom';
      out.push(at(bottom ? ANCHOR.BottomCenter : ANCHOR.TopCenter, { y: (bottom ? -1 : 1) * (g + t / 2), z },
                  strip(`${f.frameID}-x`, 'x', W, t, target, curveId)));
    }
    return out.filter(Boolean);
  };

  const stripsFor = (f) => {
    const page = f?.activePage, sz = page?.size, c = page && pictureSize(page);
    const phone = f.title === 'Android Mirror' && typeof window.sftPhoneTouch === 'function' &&
      Date.now() - (window.__sftPhoneTouchAlive || 0) < 6000;
    return cached(JSON.stringify([f.frameID, f.title, sz?.latestMeasuredPanelLocalHeight, sz?.latestMeasuredPanelWorldHeight,
                                  c?.unWidth, c?.unHeight, f.curvature?.shouldCurve ? f.curvature.curvatureTransformOriginID : null,
                                  page?.GetPanelAnchorID?.(ANCHOR.CenterRight) ?? null, cfg(), hue(), phone]),
                  () => buildStrips(f));
  };

  // ---- the gear (where the two strips would meet) and its settings panel ----
  // Saved through vr-dashboard's sftConfig binding into ~/.config/frame-tweaks/scroll-strips.json
  // (the installer window's settings page writes the same file).
  const DEFAULTS = { vertical: 'right', horizontal: 'top', thickness: 0.04, gap: 0.015, back: 0.03, color: 'tint' };
  const SWATCHES = [0, 0.08, 0.15, 0.33, 0.5, 0.58, 0.67, 0.75, 0.83, 0.92];   // hues, as the tint's 0..1
  const OPTIONS = [
    ['Vertical strip', 'vertical', [['Right', 'right'], ['Left', 'left'], ['Off', 'off']]],
    ['Horizontal strip', 'horizontal', [['Top', 'top'], ['Bottom', 'bottom'], ['Off', 'off']]],
    ['Thickness (cm)', 'thickness', [2, 2.5, 3, 4, 5, 6, 8].map((v) => [String(v), v / 100])],
    ['Gap from the window (cm)', 'gap', [0, 1, 1.5, 2, 3, 5].map((v) => [String(v), v / 100])],
    ['Set back behind the window (cm)', 'back', [0, 1, 2, 3, 5].map((v) => [String(v), v / 100])],
  ];
  const GEAR_M = 0.045, PANEL_M = 0.34;
  const settingsOpen = new Set();
  let inst = null, saveNote = '';
  const redraw = () => { try { inst?.forceUpdate(); } catch (e) {} };
  const save = (changes) => {
    const raw = { ...DEFAULTS, ...(window.__sftPatchConfig?.[NAME] ?? {}), ...changes };
    (window.__sftPatchConfig ??= {})[NAME] = raw;                 // shown at once
    if (typeof window.sftConfig === 'function') {
      try { window.sftConfig(JSON.stringify({ name: NAME, config: raw })); saveNote = ''; } catch (e) {}
    } else {
      saveNote = 'Not saved: reinstall VR windows (vr-dashboard) to keep settings.';
    }
    redraw();
  };
  const GEAR_SVG = 'M19.4 13a7.5 7.5 0 0 0 0-2l2.1-1.6-2-3.5-2.5 1a7.6 7.6 0 0 0-1.7-1L15 3h-4l-.4 2.9a7.6 7.6 0 0 0-1.7 1' +
    'l-2.5-1-2 3.5L6.6 11a7.5 7.5 0 0 0 0 2l-2.1 1.6 2 3.5 2.5-1a7.6 7.6 0 0 0 1.7 1L11 21h4l.4-2.9a7.6 7.6 0 0 0 1.7-1' +
    'l2.5 1 2-3.5zM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z';
  const settingsFor = (f) => {
    const page = f?.activePage, sz = page?.size;
    const H = sz?.latestMeasuredPanelLocalHeight, Hw = sz?.latestMeasuredPanelWorldHeight;
    if (!H || !Hw || typeof page.GetPanelAnchorID !== 'function') return [];
    const o = cfg(), raw = { ...DEFAULTS, ...(window.__sftPatchConfig?.[NAME] ?? {}) };
    const k = H / Hw, t = o.thickness * k, g = o.gap * k, h = Math.round(hue());
    const left = o.vertical === 'left', bottom = o.horizontal === 'bottom', side = left ? -1 : 1;
    const id = page.GetPanelAnchorID(left ? ANCHOR.CenterLeft : ANCHOR.CenterRight);
    if (!id) return [];
    const isOpen = settingsOpen.has(f.frameID), size = Math.max(t, GEAR_M * k * 0.8);
    const out = [el(XFORM, { key: `${f.frameID}-sgear`, parent_id: id,
                            translation: { x: side * (g + t / 2), y: (bottom ? -1 : 1) * (H / 2 + g + t / 2), z: -o.back * k } },
      el(PANEL, { key: `${f.frameID}-sgear-p`, width: size, interactive: true, only_visible_with_laser: false,
        debug_name: 'SftScrollGear', origin: ANCHOR.Center, inputFocusParams: { bCanTakeKeyboardFocus: false } },
        el('div', { style: { width: '64px', height: '64px', borderRadius: '50%', boxSizing: 'border-box', display: 'flex',
                             alignItems: 'center', justifyContent: 'center',
                             background: isOpen ? `hsla(${h}, 45%, 34%, 0.9)` : `hsla(${h}, 18%, 20%, 0.75)`,
                             border: `2px solid hsla(${h}, 60%, 68%, 0.7)` },
                    onClick: () => { isOpen ? settingsOpen.delete(f.frameID) : settingsOpen.add(f.frameID); redraw(); } },
          el('svg', { width: 40, height: 40, viewBox: '0 0 26 24' },
            el('path', { d: GEAR_SVG, fill: `hsl(${h}, 65%, 80%)`, fillRule: 'evenodd' })))))];
    if (!isOpen) return out;
    const button = (key, label, on, onClick, extra) => el('div', { key, onClick, style: {
      flex: '1 0 auto', minWidth: '58px', padding: '11px 6px', margin: '4px', borderRadius: '10px', textAlign: 'center',
      fontSize: '19px', fontWeight: on ? 700 : 500, color: on ? '#fff' : '#d8dee6',
      background: on ? `hsla(${h}, 50%, 38%, 0.95)` : 'rgba(255, 255, 255, 0.08)',
      border: `1px solid ${on ? `hsla(${h}, 60%, 70%, 0.9)` : 'rgba(255, 255, 255, 0.15)'}`, ...extra } }, label);
    const rows = [];
    const title = (key, text) => el('div', { key, style: { fontSize: '17px', color: '#9aa6b2', margin: '14px 4px 2px' } }, text);
    for (const [text, key, choices] of OPTIONS) {
      rows.push(title(`t-${key}`, text));
      rows.push(el('div', { key: `r-${key}`, style: { display: 'flex', flexWrap: 'wrap' } },
        ...choices.map(([label, value]) => button(label, label, raw[key] === value,
                                                  () => raw[key] !== value && save({ [key]: value })))));
    }
    rows.push(title('t-color', 'Colour'));
    rows.push(el('div', { key: 'r-color', style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center' } },
      button('tint', 'Passthrough tint', raw.color === 'tint', () => raw.color !== 'tint' && save({ color: 'tint' })),
      ...SWATCHES.map((v) => el('div', { key: `c${v}`, onClick: () => save({ color: v }), style: {
        width: '40px', height: '40px', margin: '5px', borderRadius: '50%', boxSizing: 'border-box',
        background: `hsl(${Math.round(v * 360)}, 60%, 55%)`,
        border: raw.color === v ? '4px solid #fff' : '2px solid rgba(255, 255, 255, 0.25)' } }))));
    rows.push(el('div', { key: 'reset', style: { display: 'flex', marginTop: '14px' } },
      button('reset', 'Reset to defaults', false, () => save(DEFAULTS))));
    if (saveNote) rows.push(el('div', { key: 'note', style: { fontSize: '15px', color: '#e0b060', margin: '8px 4px 0' } }, saveNote));
    const P = PANEL_M * k;
    out.push(el(XFORM, { key: `${f.frameID}-sset`, parent_id: id, translation: { x: side * (g + t + g + P / 2), z: -o.back * k } },     // as far back as the strips
      el(PANEL, { key: `${f.frameID}-sset-p`, width: P, interactive: true, only_visible_with_laser: false,
        debug_name: 'SftScrollSettings', origin: ANCHOR.Center, inputFocusParams: { bCanTakeKeyboardFocus: false } },
        el('div', { style: { width: '460px', boxSizing: 'border-box', padding: '16px 14px', borderRadius: '18px',
                             background: 'rgba(22, 27, 34, 0.94)', border: `1px solid hsla(${h}, 60%, 68%, 0.5)`, color: '#e8ecf0' } },
          el('div', { style: { display: 'flex', alignItems: 'center' } },
            el('div', { style: { flex: '1', fontSize: '24px', fontWeight: 700 } }, 'Scroll strips'),
            el('div', { onClick: () => { settingsOpen.delete(f.frameID); redraw(); },
                        style: { fontSize: '28px', padding: '0 10px', color: '#9aa6b2' } }, '✕')),
          ...rows,
          el('div', { style: { fontSize: '15px', color: '#9aa6b2', margin: '10px 4px 0' } },
             'For every window. Changes show at once.')))));
    return out;
  };
  const gearFor = (f) => {
    const sz = f?.activePage?.size;
    return cached(JSON.stringify(['gear', f.frameID, sz?.latestMeasuredPanelLocalHeight, sz?.latestMeasuredPanelWorldHeight,
                                  f.activePage?.GetPanelAnchorID?.(ANCHOR.CenterRight) ?? null, cfg(),
                                  window.__sftPatchConfig?.[NAME] ?? null, hue(), settingsOpen.has(f.frameID), saveNote]),
                  () => settingsFor(f));
  };

  class SftScrollStrips extends Base {
    componentDidMount() { inst = this; this.timer = setInterval(() => { try { this.forceUpdate(); } catch (e) {} }, 500); }
    componentWillUnmount() { clearInterval(this.timer); }
    render() {
      try {
        if (!learn()) return null;
        const out = [];
        for (const f of FS.frames ?? []) {
          const dock = f?.docking?.dockLocation;
          if (dock === WORLD || (dock === DASH && f === DS.activeFrame && DS.isFullyVisible)) out.push(...stripsFor(f), ...gearFor(f));
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
