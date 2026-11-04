// frame-tweaks phone-touch: laser clicks on the Android Mirror window land where you aim.
// The Steam session maps the laser wrongly on a window narrower than its screen (every click on the
// upright phone landed at the window's left edge). So a see-through layer of ours covers the mirror
// window and takes the laser instead: where you press, drag and let go goes to phone-touch (through
// its sftPhoneTouch binding), which sends them to the phone as touches; a press also gives the mirror
// the keyboard focus, as a click on the window would. The layer is there only while phone-touch runs
// (it sets window.__sftPhoneTouchAlive every 2 s). A gear below the window's
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
  const NAME = 'phone-touch', VERSION = 33;
  const TITLE = 'Android Mirror';             // the mirror window's title (phone sets it; English, as it's matched)
  const TOP_CENTER = 1, CENTER_LEFT = 3;      // panel anchors
  // Text in the user's language: sft-dashboard sends window.__sftI18n for T(text), N(text).
  const T = (s) => window.__sftI18n?.t?.[s] ?? s, N = (s) => s;
  const LIFT_M = 0.002;                       // the layer floats 2 mm in front of the picture
  const stats = { downs: 0, moves: 0, ups: 0, wheels: 0, lastWheel: null, hovers: 0, leaves: 0, lostUps: 0, noButtons: 0, strayZeros: 0, focusPushes: 0, trail: [] };
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
  // A let-go that went missing shows as moves with no button held (ev.buttons 0) while the
  // touch goes on. But the laser sends one such move right after each press (5 ms later, then its
  // moves report the button again), and that one ended every press there, so a swipe reached the
  // phone as a tap. So: only 250 ms of nothing but button-less moves means the let-go was lost; a
  // touch whose events never show a button at all ends only on a real let-go (mouseup/pointerup)
  // or the next press.
  const LOST_LET_GO_MS = 250;
  const letGoMissing = (ev, now = Date.now()) => {
    if (ev.buttons !== 0) { touch.buttons = true; touch.zeroSince = 0; return false; }
    if (!touch.buttons) { stats.noButtons++; return false; }
    if (!touch.zeroSince) { touch.zeroSince = now; stats.strayZeros++; return false; }
    return now - touch.zeroSince >= LOST_LET_GO_MS;
  };
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
    if (letGoMissing(ev)) { stats.lostUps++; return onUp(ev); }
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
    if (touch && letGoMissing(ev)) { stats.lostUps++; onUp(ev); }
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
  // Keys (a keyboard, Steam's keyboard) go to the window that has the dashboard's input focus,
  // which a click on a window gives it. Here the click lands on our layer, which can't take focus:
  // focus_target_sgid passes it on to the mirror, as SteamVR's own grab handle does. Should it not
  // have arrived a moment later, the mirror asks for it.
  const focusMirror = (f) => setTimeout(() => {
    const focus = f.activePage?.inputFocus;
    if (focus && !focus.mainPanelHasFocus) { stats.focusPushes++; focus.PushInputFocus?.(); }
  }, 300);
  const buildLayer = (f) => {
    const page = f.activePage, sz = page?.size;
    const H = sz?.latestMeasuredPanelLocalHeight, Hw = sz?.latestMeasuredPanelWorldHeight, c = page && pictureSize(page);
    const id = c && typeof page.GetPanelAnchorID === 'function' && page.GetPanelAnchorID(TOP_CENTER);
    if (!H || !Hw || !id) return null;
    const W = H * c.w / c.h, k = H / Hw;
    // A curved window: bend the layer around the same origin, so it stays on the picture.
    const curveId = f.curvature?.shouldCurve ? f.curvature.curvatureTransformOriginID : undefined;
    const pxW = 240, pxH = Math.round(pxW * c.h / c.w);         // small page element, same shape
    const over = hidden(pxW, pxH);
    return el(XFORM, { key: `${f.frameID}-sft-touch`, parent_id: id, translation: { y: -H / 2, z: LIFT_M * k } },
      el(PANEL, { key: `${f.frameID}-sft-touch-p`, width: W, interactive: true, only_visible_with_laser: false,
        debug_name: 'SftPhoneTouch', origin: 4, inputFocusParams: { bCanTakeKeyboardFocus: false },
        focus_target_sgid: page.mainPanelSGID,
        ...(curveId ? { curvature_origin_id: curveId } : {}) },
        el('div', { style: { width: `${pxW}px`, height: `${pxH}px`, background: 'rgba(0, 0, 0, 0)', position: 'relative' },
          onWheel: (ev) => onWheel(ev, c),
          onMouseMove: (ev) => onHover(ev, c),
          onMouseLeave: onLeave,
          onMouseDown: (ev) => {
            stats.downs++;
            mark('down');
            if (touch) onUp(ev);                    // a new press ends a touch whose let-go went missing
            touch = { rect: ev.currentTarget.getBoundingClientRect(), size: c, buttons: ev.buttons !== 0, zeroSince: 0 };
            send('down', ev);
            focusMirror(f);
            window.addEventListener('mousemove', onMove, true);
            window.addEventListener('mouseup', onUp, true);
            window.addEventListener('pointerup', onUp, true);
          } }, ...over)));
  };

  // ---- a screen the phone hides from the mirror ----
  // An app can hide its screen from mirroring (Android's FLAG_SECURE: the PIN or fingerprint
  // prompt, banking apps, password managers): the mirror shows black. phone-touch sees the focused
  // window marked SECURE and sets window.__sftPhoneSecure ("screen", or "biometric" for the phone's
  // fingerprint or face prompt, which wants the sensor rather than a PIN); a notice in the picture says why, with
  // two ways to unlock it blind:
  //  - Type PIN: a keypad of ours that types on the phone (Android's digit keys, Delete, Enter, as
  //    a keyboard plugged into the phone would; phone-touch's UNLOCK_KEYS), whatever its layout.
  //    It shows one dot per digit, never the digits; nothing of it is logged or kept.
  //  - Where the digits are: a reference PIN pad over the picture, where a lock screen usually has
  //    them, for a screen that doesn't take typed keys: taps go through it to the phone (its
  //    digits take no clicks), and arrows around it nudge it onto the phone's own layout.
  // Both stay for the session (window.__sftPhoneUnlock, __sftPhoneKeypad); the typing pad goes by
  // itself once the screen isn't hidden any more (unlocked).
  const keypad = (window.__sftPhoneKeypad ??= { on: false, dx: 0, dy: 0 });
  const unlock = (window.__sftPhoneUnlock ??= { on: false, count: 0, wasSecure: false });
  const NUDGE = 0.01;                                // of the picture, per arrow press
  const KEYPAD_SVG = 'M5 3h3v3H5zM10.5 3h3v3h-3zM16 3h3v3h-3zM5 8.5h3v3H5zM10.5 8.5h3v3h-3zM16 8.5h3v3h-3z' +
    'M5 14h3v3H5zM10.5 14h3v3h-3zM16 14h3v3h-3zM10.5 19.5h3v3h-3z';
  // A control in the picture: a click acts here and never reaches the phone as a touch.
  const own = (fn) => ({ onMouseDown: (ev) => { ev.stopPropagation(); ev.preventDefault(); buzz('Snap'); },
                         onMouseUp: (ev) => ev.stopPropagation(),
                         onClick: (ev) => { ev.stopPropagation(); fn(); redraw(); },
                         onMouseEnter: () => buzz('Enter') });
  const FINGERPRINT_SVG = 'M12 3a8 8 0 0 0-8 8M12 3a8 8 0 0 1 8 8v1M8 20a14 14 0 0 1-1.5-6.5 5.5 5.5 0 0 1 11 0v.5' +
    'M12 11v3a9 9 0 0 0 2 6M9.5 13.5a2.5 2.5 0 0 1 5 0V15M15 19a12 12 0 0 0 .5-3';
  const OUTLINE_SVG = 'M4 2h4v4H4zM10 2h4v4h-4zM16 2h4v4h-4zM4 8h4v4H4zM10 8h4v4h-4zM16 8h4v4h-4zM4 14h4v4H4zM10 14h4v4h-4z' +
    'M16 14h4v4h-4zM10 20h4v3h-4z';
  const iconButton = (h, on, svg, outline, tip, fn) =>
    el('div', { ...own(fn), title: tip,
                style: { pointerEvents: 'auto', flex: '0 0 auto', width: '26px', height: '26px', borderRadius: '6px',
                         display: 'flex', alignItems: 'center', justifyContent: 'center',
                         background: on ? `hsla(${h}, 50%, 38%, 0.95)` : 'rgba(255, 255, 255, 0.1)',
                         border: `1px solid hsla(${h}, 60%, 70%, 0.8)` } },
      el('svg', { width: 18, height: 18, viewBox: '0 0 24 24' },
        el('path', outline ? { d: svg, fill: 'none', stroke: `hsl(${h}, 65%, 85%)`, strokeWidth: 1.4 }
                           : { d: svg, fill: `hsl(${h}, 65%, 85%)` })));
  const typingPad = (pxW, pxH, h) => {
    const w = pxW * 0.72, x = (pxW - w) / 2, y = pxH * 0.22;
    const press = (k) => { call({ a: 'key', k }); unlock.count = k === 'del' ? Math.max(0, unlock.count - 1)
                                                               : k === 'enter' ? 0 : unlock.count + 1; };
    const key = (label, k, tip) => el('div', { key: `k${label}`, ...own(() => press(k)), ...(tip ? { title: T(tip) } : {}), style: {
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '30px', margin: '3px', borderRadius: '8px', fontSize: '16px', fontWeight: 600, color: '#fff',
        background: 'rgba(255, 255, 255, 0.12)', border: `1px solid hsla(${h}, 60%, 70%, 0.5)` } }, label);
    const digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((d) => key(d, d));
    return el('div', { key: 'typing', style: { position: 'absolute', left: `${x}px`, top: `${y}px`, width: `${w}px`,
        boxSizing: 'border-box', padding: '8px', borderRadius: '12px', background: 'rgba(22, 27, 34, 0.95)',
        border: `1px solid hsla(${h}, 60%, 68%, 0.7)` } },
      el('div', { style: { display: 'flex', alignItems: 'center', marginBottom: '4px' } },
        el('div', { style: { flex: '1', textAlign: 'center', color: '#e8ecf0', fontSize: '16px', letterSpacing: '4px',
                             minHeight: '20px' } }, '●'.repeat(Math.min(unlock.count, 16))),
        el('div', { ...own(() => { unlock.on = false; unlock.count = 0; }), title: T('Close'),
                    style: { fontSize: '14px', color: '#9aa6b2', padding: '0 4px' } }, '✕')),
      el('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)' } },
        ...digits, key('⌫', 'del', N('Delete the last digit')), key('0', '0'), key('↵', 'enter', N('Enter: send the PIN'))),
      el('div', { ...own(() => call({ a: 'show-pin' })), style: { marginTop: '4px', textAlign: 'center',
          padding: '6px', borderRadius: '8px', fontSize: '11px', color: '#e8ecf0', background: 'rgba(255, 255, 255, 0.08)',
          border: `1px solid hsla(${h}, 60%, 70%, 0.35)` } }, T('Wake / show PIN')));
  };
  const hidden = (pxW, pxH) => {
    const out = [], h = hueOf(), secure = !!window.__sftPhoneSecure;
    if (unlock.wasSecure && !secure) { unlock.on = false; unlock.count = 0; }      // (unlocked: done)
    unlock.wasSecure = secure;
    if (secure) {
      out.push(el('div', { key: 'secure', style: { position: 'absolute', left: '5%', top: '4%', width: '90%',
          boxSizing: 'border-box', padding: '6px 8px', borderRadius: '8px', background: 'rgba(22, 27, 34, 0.92)',
          border: `1px solid hsla(${h}, 60%, 68%, 0.6)`, color: '#e8ecf0', fontSize: '10px', lineHeight: 1.35,
          display: 'flex', alignItems: 'center', gap: '6px', pointerEvents: 'none' } },
        el('div', { style: { flex: '1' } }, window.__sftPhoneSecure === 'biometric'
          ? '👆 ' + T('Your phone asks for your fingerprint or face: use its sensor. Or press Use PIN on the phone and type your PIN here.')
          : '🔒 ' + T('The app on your phone hides this screen from mirroring (a privacy setting): it shows only on the phone.')),
        iconButton(h, unlock.on, KEYPAD_SVG, false, T('Type your PIN on the phone'),
                   () => { unlock.on = !unlock.on; unlock.count = 0; }),
        iconButton(h, keypad.on, OUTLINE_SVG, true, T('Show where a lock screen has its digits'),
                   () => { keypad.on = !keypad.on; })));
    }
    // The fingerprint prompt: a fingerprint where the phone's sensor is (phone-touch reads it from
    // the sensor's overlay window, or guesses a Pixel's spot), so a thumb finds it without seeing.
    const spot = window.__sftPhoneSecure === 'biometric' && window.__sftPhoneSensor;
    if (spot) {
      const d = Math.max(24, (spot.d || 0.11) * pxW);
      out.push(el('div', { key: 'sensor', style: { position: 'absolute', left: `${spot.u * pxW - d / 2}px`,
          top: `${spot.v * pxH - d / 2}px`, width: `${d}px`, height: `${d}px`, pointerEvents: 'none',
          display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%',
          border: `2px solid hsla(${h}, 70%, 75%, 0.8)`, background: 'rgba(255, 255, 255, 0.06)' } },
        el('svg', { width: d * 0.7, height: d * 0.7, viewBox: '0 0 24 24' },
          el('path', { d: FINGERPRINT_SVG, fill: 'none', stroke: `hsl(${h}, 70%, 82%)`, strokeWidth: 1.5,
                       strokeLinecap: 'round' }))));
    }
    if (unlock.on) out.push(typingPad(pxW, pxH, h));
    if (!keypad.on) return out;
    // Where a phone's lock-screen PIN pad usually is: the lower half, most of the width (a Pixel's).
    const gw = pxW * 0.66, gh = pxH * 0.36;
    const cx = pxW * (0.5 + keypad.dx), cy = pxH * (0.66 + keypad.dy);
    const left = cx - gw / 2, top = cy - gh / 2;
    const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '⌫', '0', '↵'];
    out.push(el('div', { key: 'pad', style: { position: 'absolute', left: `${left}px`, top: `${top}px`,
        width: `${gw}px`, height: `${gh}px`, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
        gridTemplateRows: 'repeat(4, 1fr)', pointerEvents: 'none' } },
      ...keys.map((d) => el('div', { key: d, style: { display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: d.match(/\d/) ? 'rgba(255, 255, 255, 0.85)' : 'rgba(255, 255, 255, 0.45)', fontSize: '15px', fontWeight: 600,
          border: `1px solid hsla(${h}, 60%, 70%, 0.35)`, borderRadius: '50%', margin: '3px',
          background: 'rgba(255, 255, 255, 0.04)' } }, d))));
    // The arrows, around it: each moves it a step that way.
    const A = 16, gap = 3;
    const arrows = [['↖', -1, -1], ['↑', 0, -1], ['↗', 1, -1], ['←', -1, 0], ['→', 1, 0], ['↙', -1, 1], ['↓', 0, 1], ['↘', 1, 1]];
    for (const [label, ax, ay] of arrows) {
      const x = ax < 0 ? left - A - gap : ax > 0 ? left + gw + gap : cx - A / 2;
      const y = ay < 0 ? top - A - gap : ay > 0 ? top + gh + gap : cy - A / 2;
      out.push(el('div', { key: `n${label}`, ...own(() => { keypad.dx += ax * NUDGE; keypad.dy += ay * NUDGE; }),
        title: T('Move the keypad'),
        style: { position: 'absolute', left: `${x}px`, top: `${y}px`, width: `${A}px`, height: `${A}px`,
                 borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px',
                 color: '#e8ecf0', background: `hsla(${h}, 30%, 25%, 0.85)`, border: `1px solid hsla(${h}, 60%, 70%, 0.6)` } },
        label));
    }
    return out;
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
    // (scrcpy's clipboard sync: the Frame's to the phone when you paste in the mirror, the phone's
    // here whenever it copies; off: --no-clipboard-autosync)
    [N('Clipboard with the phone'), 'PHONE_CLIPBOARD', [[N('Shared'), 'both'], [N('Not shared'), 'off']], true],
    // (minutes; `phone` reads it at each check, so it applies at once, counted from the change)
    [N('Disconnect by itself after'), 'PHONE_TIMEOUT',
     [[N('Never'), '0'], [N('15 min'), '15'], [N('30 min'), '30'], [N('1 h'), '60'], [N('2 h'), '120'], [N('4 h'), '240'],
      [N('8 h'), '480']], false],
    // The hardware-key buttons (hwKeys): which side of the mirror, then each on or off
    [N('Buttons'), 'PHONE_KEY_SIDE', [[N('Below'), 'below'], [N('Above'), 'above'], [N('Left'), 'left'], [N('Right'), 'right']],
     false],
    [N('Back button'), 'PHONE_KEY_BACK', [[N('On'), 'on'], [N('Off'), 'off']], false],
    [N('App switcher button'), 'PHONE_KEY_RECENTS', [[N('On'), 'on'], [N('Off'), 'off']], false],
    [N('Volume up button'), 'PHONE_KEY_VOLUP', [[N('On'), 'on'], [N('Off'), 'off']], false],
    [N('Volume down button'), 'PHONE_KEY_VOLDOWN', [[N('On'), 'on'], [N('Off'), 'off']], false],
    [N('Power button'), 'PHONE_KEY_POWER', [[N('On'), 'on'], [N('Off'), 'off']], false],
    [N('Notifications button'), 'PHONE_KEY_NOTIFY', [[N('On'), 'on'], [N('Off'), 'off']], false],
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
  // The window the dashboard showed, for when a returning mirror came up there and is floated away
  // (a reconnect, after the phone slept: the new window docks, and the dashboard shows it; floated
  // back to its place, it left the dashboard showing nothing).
  let lastShown = null;
  const showAgain = () => {
    const ctl = L.walk((fb) => typeof fb.stateNode?.switchToFrameInternal === 'function')?.stateNode;
    if (!ctl) return;
    const g = lastShown != null ? FS.GetFrame?.(lastShown) : null;
    if (g && g.docking?.dockLocation === DASH) ctl.switchToFrameInternal(g, undefined, 'sft-phone-touch');
    else ctl.switchToHomeOverlay?.();         // (the dashboard's own choice when a shown window goes)
  };
  const watchMirrors = () => {
    const a = DS.activeFrame;
    // (Not Android Mirror's own windows: its "Starting the mirror…" splash, shown during a restart,
    // was taken for the window before, and the dashboard went home once it closed.)
    if (a && !a.title?.startsWith(TITLE) && a.docking?.dockLocation === DASH) lastShown = a.frameID;
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
        const shown = DS.activeFrameID === f.frameID;
        // The dashboard's own SetDockLocation: Float grab's wrapper would pick it up in your hand.
        const own = d.__sftOrigSetDock?.orig ?? d.SetDockLocation;
        own.call(d, WORLD);
        if (shown) showAgain();                 // (the dashboard showed it: back to what it showed before)
        return;                                 // (its floating component mounts next: placed then)
      }
      // A restarted mirror can come up floating already, and the dashboard then shows it, an empty
      // space (Back to the previous window never saw it docked): back to the window it showed before.
      if (!c.backShown && DS.activeFrameID === f.frameID) { c.backShown = true; showAgain(); }
      const m = mover(f);
      if (!m?.state?.xfTransform) return;       // (not mounted yet: next tick)
      if (m.state.sParentDevice || d.m_bBeingDragged) { carry = null; return; }   // (you took it: yours)
      // Put back, and kept there for 6 s: the dashboard places the window again once it takes the
      // phone's shape (phone-fit resizes it just after it appears), which undid a single move.
      c.placedAt ??= Date.now();
      const at = m.state.xfTransform.translation, want = c.xf.translation;
      if (Math.abs(at.x - want.x) + Math.abs(at.y - want.y) + Math.abs(at.z - want.z) > 0.001) {
        m.setState({ xfTransform: clone(c.xf) });
      }
      if (Date.now() - c.placedAt > 6000) {
        carry = null;
        snapshot(f);
      }
    } catch (e) {
      carry = null;                             // (the dashboard changed: it stays where it came up)
    }
  };
  const DEFAULTS = { PHONE_MAX_SIZE: '1024', PHONE_BIT_RATE: '2M', PHONE_MAX_FPS: '60', PHONE_STICK_SPEED: '15',
                     PHONE_CLIPBOARD: 'both', PHONE_TIMEOUT: '60', PHONE_KEY_SIDE: 'below', PHONE_KEY_BACK: 'off', PHONE_KEY_RECENTS: 'off',
                     PHONE_KEY_VOLUP: 'off', PHONE_KEY_VOLDOWN: 'off', PHONE_KEY_POWER: 'off', PHONE_KEY_NOTIFY: 'off' };
  const settingsOpen = new Set();               // frame IDs whose panel is showing
  let pending = false;                          // a picture change waits for "Restart stream"
  let dragKey = null, dragMoved = false;        // a button being dragged by its handle (settings)
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
                    title: T(isOpen ? N('Close the settings') : N('Settings: the stream, the buttons and where they go')),
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
    const isToggle = (choices) => choices.length === 2 && choices[0][1] === 'on' && choices[1][1] === 'off';
    // The on/off ones (the mirror's buttons): one compact row each, a grab handle, the name and a
    // switch. Drag a handle up or down to change the buttons' order by the mirror.
    const order = keyOrder(conf);
    const moveTo = (name) => {
      if (!dragKey || dragKey === name) return;
      const next = order.filter((n) => n !== dragKey);
      next.splice(next.indexOf(name) + (order.indexOf(dragKey) < order.indexOf(name) ? 1 : 0), 0, dragKey);
      window.__sftPhoneTouchConf = { ...conf, PHONE_KEY_ORDER: next.join(',') };
      dragMoved = true;
      redraw();
    };
    const endDrag = () => {
      if (dragKey && dragMoved) call({ a: 'set', conf: { PHONE_KEY_ORDER: (window.__sftPhoneTouchConf || {}).PHONE_KEY_ORDER } });
      dragKey = null;
      dragMoved = false;
      redraw();
    };
    const toggle = (title, key) => {
      const on = conf[key] === 'on', name = HW.find((x) => x[0] === key)?.[1];
      return el('div', { key: `s-${key}`, ...tap(), onClick: () => {
          window.__sftPhoneTouchConf = { ...conf, [key]: on ? 'off' : 'on' };
          call({ a: 'set', conf: { [key]: on ? 'off' : 'on' } });
          redraw();
        }, onMouseEnter: () => { buzz('Enter'); moveTo(name); },
        style: { display: 'flex', alignItems: 'center', padding: '7px 6px', margin: '2px 0', borderRadius: '8px',
                 background: dragKey === name ? `hsla(${h}, 40%, 30%, 0.8)` : 'rgba(255, 255, 255, 0.04)' } },
        el('div', { title: T('Drag to change the order'), style: { padding: '0 10px 0 4px', fontSize: '22px', color: '#9aa6b2',
                                                                 cursor: 'grab' },
                    onMouseDown: (ev) => {
                      ev.stopPropagation(); ev.preventDefault(); buzz('Snap');
                      dragKey = name; dragMoved = false;
                      window.addEventListener('mouseup', endDrag, { once: true, capture: true });
                      redraw();
                    },
                    onClick: (ev) => ev.stopPropagation() }, '⠿'),
        el('div', { style: { flex: '1', fontSize: '18px', color: '#d8dee6' } }, T(title)),
        el('div', { style: { width: '46px', height: '26px', borderRadius: '13px', position: 'relative',
                             background: on ? `hsla(${h}, 50%, 45%, 0.95)` : 'rgba(255, 255, 255, 0.15)',
                             border: `1px solid ${on ? `hsla(${h}, 60%, 70%, 0.9)` : 'rgba(255, 255, 255, 0.25)'}` } },
          el('div', { style: { position: 'absolute', top: '3px', left: on ? '23px' : '3px', width: '20px', height: '20px',
                               borderRadius: '50%', background: '#fff' } })));
    };
    let toggles = false;
    for (const [title, key, choices, restart] of OPTIONS) {
      if (key === 'PHONE_KEY_SIDE') continue;          // (on the buttons' heading row, below)
      if (isToggle(choices)) {
        if (!toggles) {
          toggles = true;
          // Their heading and their side of the mirror on one row: "Buttons  Below Above Left Right".
          const side = OPTIONS.find((o) => o[1] === 'PHONE_KEY_SIDE');
          rows.push(el('div', { key: 'buttons-side', style: { display: 'flex', alignItems: 'center', margin: '10px 0 2px' } },
            el('div', { style: { fontSize: '17px', color: '#9aa6b2', margin: '0 8px 0 4px', whiteSpace: 'nowrap' } }, T(side[0])),
            ...side[2].map(([label, value]) => el('div', { key: value, ...tap(), onClick: () => {
                if (conf.PHONE_KEY_SIDE === value) return;
                window.__sftPhoneTouchConf = { ...conf, PHONE_KEY_SIDE: value };
                call({ a: 'set', conf: { PHONE_KEY_SIDE: value } });
                redraw();
              }, style: { flex: '1 1 0', minWidth: '0', padding: '8px 2px', margin: '2px', borderRadius: '8px', textAlign: 'center',
                          fontSize: '16px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                          fontWeight: conf.PHONE_KEY_SIDE === value ? 700 : 500,
                          color: conf.PHONE_KEY_SIDE === value ? '#fff' : '#d8dee6',
                          background: conf.PHONE_KEY_SIDE === value ? `hsla(${h}, 50%, 38%, 0.95)` : 'rgba(255, 255, 255, 0.08)',
                          border: `1px solid ${conf.PHONE_KEY_SIDE === value ? `hsla(${h}, 60%, 70%, 0.9)`
                                                                              : 'rgba(255, 255, 255, 0.15)'}` } },
              T(label)))));
          // (all of them here, in the buttons' order: the rest of OPTIONS' on/off ones are skipped)
          const named = order.map((n) => HW.find((x) => x[1] === n)?.[0]);
          for (const k2 of named) {
            const opt = OPTIONS.find((o) => o[1] === k2);
            if (opt) rows.push(toggle(opt[0], k2));
          }
        }
        continue;
      }
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
                       // (and left of the buttons, when they're a column on the left)
                       translation: { x: -(GAP_M * k + (beside ? GEAR_M * k + GAP_M * k : 0) +
                                           (conf.PHONE_KEY_SIDE === 'left' ? keysOut(f, k, 'left', beside) + KEY_M * k : 0) +
                                           SETTINGS_M * k / 2),
                                      z: LIFT_M * k } },
      el(PANEL, { key: `${f.frameID}-sft-set-p`, width: SETTINGS_M * k, interactive: true, only_visible_with_laser: false,
        debug_name: 'SftPhoneSettings', origin: 4, inputFocusParams: { bCanTakeKeyboardFocus: false } },
        // (zoom: drawn smaller in the shared page, so it fits; it's shown at the same size in VR)
        el('div', { style: { width: `${pxW}px`, boxSizing: 'border-box', padding: '16px 14px', borderRadius: '18px',
                             background: 'rgba(22, 27, 34, 0.94)', border: `1px solid hsla(${h}, 60%, 68%, 0.5)`,
                             color: '#e8ecf0', fontFamily: 'inherit', zoom: 0.62, textAlign: 'left' } },
          el('div', { style: { display: 'flex', alignItems: 'center' } },
            el('div', { style: { flex: '1', fontSize: '24px', fontWeight: 700 } }, T('Android Mirror')),
            el('div', { ...tap(), onClick: () => { settingsOpen.delete(f.frameID); redraw(); }, title: T('Close the settings'),
                        style: { fontSize: '28px', padding: '0 10px', color: '#9aa6b2' } }, '✕')),
          ...rows,
          el('div', { style: { fontSize: '15px', color: '#9aa6b2', margin: '10px 4px 0' } },
             T('Picture and smoothness apply when the stream restarts; joystick speed and disconnecting at once.')))));
  };
  // The phone's hardware keys, as buttons on one side of the window (PHONE_KEY_SIDE; the ones the
  // settings turn on): Back, App switcher (recent apps), Volume up and down, sent as the phone's own
  // keys (phone-touch HW_KEYS).
  const BOTTOM_CENTER = 7, CENTER_RIGHT = 5, BAR_M = 0.06, TOP_M = 0.06, KEY_M = 0.05;
  // How far the buttons' near edge is from the window, on that side: beyond a scroll strip there
  // (scroll-strips' room()), below also beyond the grab bar, above also beyond SteamVR's "Enter
  // Gamepad Mode" over the window (TOP_M), left also beyond the gear when it sits beside the window.
  const stripRoom = () => { try { return window.__sftPatches?.['scroll-strips']?.room?.() ?? {}; } catch (e) { return {}; } };
  const keysOut = (f, k, side, beside) => {
    const room = stripRoom(), edge = { below: 'bottom', above: 'top', left: 'left', right: 'right' }[side];
    return (GAP_M + (room[edge] || 0) + (side === 'below' ? BAR_M : side === 'above' ? TOP_M : 0) + (side === 'left' && beside ? GEAR_M + GAP_M : 0)) * k;
  };
  const HW = [['PHONE_KEY_BACK', 'back', 'M15 5 8 12l7 7', N('Back')],
              ['PHONE_KEY_RECENTS', 'recents', 'M6 6h12v12H6z', N('App switcher')],
              ['PHONE_KEY_VOLDOWN', 'vol_down', 'M4 9v6h4l5 4V5L8 9zM16 12h5', N('Volume down')],
              ['PHONE_KEY_VOLUP', 'vol_up', 'M4 9v6h4l5 4V5L8 9zM16 12h5M18.5 9.5v5', N('Volume up')],
              ['PHONE_KEY_POWER', 'power', 'M12 3v8M7.5 6.2a7 7 0 1 0 9 0', N('Power')],
              ['PHONE_KEY_NOTIFY', 'notifications', 'M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0', N('Notifications')]];
  // The buttons' order (phone-touch's PHONE_KEY_ORDER, names comma-separated; the gear's panel
  // changes it by dragging the handles), any it leaves out last in the usual order.
  const keyOrder = (conf) => {
    const named = [...new Set(String(conf.PHONE_KEY_ORDER || '').split(','))].filter((n) => HW.some((x) => x[1] === n));
    return [...named, ...HW.map((x) => x[1]).filter((n) => !named.includes(n))];
  };
  // One panel of a constant size, always there while the mirror is (the buttons turned off are
  // only hidden inside it): a panel made anew, or resized, as buttons were turned on or off was
  // drawn for a moment at its picture's size in the middle of the mirror before going below it.
  // A row below or above the window, or a column left or right of it (PHONE_KEY_SIDE).
  const hwKeys = (f, k, H, beside) => {
    const conf = window.__sftPhoneTouchConf || {};
    const on = keyOrder(conf).map((n) => HW.find((x) => x[1] === n)).filter((x) => x && conf[x[0]] === 'on');
    const side = ['below', 'above', 'left', 'right'].includes(conf.PHONE_KEY_SIDE) ? conf.PHONE_KEY_SIDE : 'below';
    const anchor = { below: BOTTOM_CENTER, above: TOP_CENTER, left: CENTER_LEFT, right: CENTER_RIGHT }[side];
    const id = typeof f.activePage?.GetPanelAnchorID === 'function' && f.activePage.GetPanelAnchorID(anchor);
    if (!id) return null;
    const h = hueOf(), px = 60, column = side === 'left' || side === 'right', d = keysOut(f, k, side, beside) + KEY_M * k / 2;
    const at = { below: { y: -d }, above: { y: d }, left: { x: -d }, right: { x: d } }[side];
    // (the panel's key has the side in it: a panel turned from a row to a column is a new one,
    // not one resized, which would be drawn for a moment in the middle of the mirror)
    return el(XFORM, { key: `${f.frameID}-sft-keys-${column ? 'c' : 'r'}`, parent_id: id, translation: { ...at, z: LIFT_M * k } },
      el(PANEL, { key: `${f.frameID}-sft-keys-p-${column ? 'c' : 'r'}`, width: KEY_M * k * (column ? 1 : HW.length),
        interactive: on.length > 0, only_visible_with_laser: false, debug_name: 'SftPhoneKeys', origin: 4,
        inputFocusParams: { bCanTakeKeyboardFocus: false } },
        el('div', { style: { display: 'flex', flexDirection: column ? 'column' : 'row', justifyContent: 'center',
                             alignItems: 'center', width: `${px * (column ? 1 : HW.length)}px`,
                             height: `${px * (column ? HW.length : 1)}px` } },
          ...on.map(([, k2, d, label]) => el('div', { key: k2, ...tap(), title: T(label),
              onClick: () => call({ a: 'hwkey', k: k2 }),
              style: { width: `${px - 8}px`, height: `${px - 8}px`, margin: '4px', borderRadius: '50%',
                       display: 'flex', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box',
                       background: `hsla(${h}, 18%, 20%, 0.8)`, border: `2px solid hsla(${h}, 60%, 68%, 0.7)` } },
            el('svg', { width: 30, height: 30, viewBox: '0 0 24 24' },
              el('path', { d, fill: 'none', stroke: `hsl(${h}, 65%, 82%)`, strokeWidth: 2,
                           strokeLinecap: 'round', strokeLinejoin: 'round' })))))));
  };
  const buildExtras = (f) => {
    const page = f.activePage, sz = page?.size;
    const H = sz?.latestMeasuredPanelLocalHeight, Hw = sz?.latestMeasuredPanelWorldHeight;
    const id = typeof page?.GetPanelAnchorID === 'function' && page.GetPanelAnchorID(CENTER_LEFT);
    if (!H || !Hw || !id) return [];
    const k = H / Hw, c = pictureSize(page);
    const beside = f.docking?.dockLocation === DASH && c && c.w < c.h;      // upright, docked
    return [gear(f, k, H, id, beside), settingsOpen.has(f.frameID) ? settings(f, k, id, beside) : null,
            hwKeys(f, k, H, beside)];
  };

  const sizes = (f) => {
    const sz = f.activePage?.size, c = f.activePage && pictureSize(f.activePage);
    return [f.frameID, sz?.latestMeasuredPanelLocalHeight, sz?.latestMeasuredPanelWorldHeight, c?.w, c?.h,
            f.curvature?.shouldCurve ? f.curvature.curvatureTransformOriginID : null,
            f.activePage?.GetPanelAnchorID?.(TOP_CENTER) ?? null];
  };
  const layer = (f) => cached(JSON.stringify(['layer', ...sizes(f), f.activePage?.mainPanelSGID ?? null,
                                              window.__sftPhoneSecure || '', window.__sftPhoneSensor ?? null, keypad, unlock,
                                              window.__sftI18n?.lang ?? null, hueOf()]),
                              () => buildLayer(f));
  const extras = (f) => cached(JSON.stringify(['extras', window.__sftI18n?.lang ?? null, ...sizes(f), f.docking?.dockLocation,
                                               settingsOpen.has(f.frameID), pending, hueOf(),
                                               window.__sftPhoneTouchConf ?? null, stripRoom()]), () => buildExtras(f));

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
  const carryTimer = setInterval(() => { try { watchMirrors(); placeCarried(); } catch (e) {} }, 100);
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
