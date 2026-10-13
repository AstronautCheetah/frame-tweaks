// steam-frame-tweaks phone-rotate: a floating window that rotates (the Android Mirror when you turn
// the phone) keeps its size, just turned. SteamVR keeps a floating window's width when its shape
// changes, so an upright phone turned sideways shrank to a thin strip as wide as the upright one.
// When a window's picture turns (upright <-> sideways, same shape), this scales it so its long
// side stays as long as before.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// requires: UndockedOverlay.startFloatingWindowMove | startFloatingWindowMove(e){
// requires: floating transform state | this.setState({xfTransform:r})
// requires: EDockLocation.World = 4 | e[e.World=4]="World"
(() => {
  const NAME = 'phone-rotate', VERSION = 1, WORLD = 4;
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore;
  if (!FS) return 'not patched: dashboard objects missing';

  // The React components that float windows, by frame.
  const movers = () => {
    const out = new Map();
    const rootEl = document.getElementById('root') ?? document.body.firstElementChild;
    const key = rootEl && Object.keys(rootEl).find((k) => k.startsWith('__reactContainer$'));
    if (!key) return out;
    const stack = [rootEl[key]];
    let n = 0;
    while (stack.length && n++ < 50000) {
      const fb = stack.pop();
      const s = fb.stateNode;
      if (s && typeof s.startFloatingWindowMove === 'function' && s.props?.frame) out.set(s.props.frame, s);
      if (fb.sibling) stack.push(fb.sibling);
      if (fb.child) stack.push(fb.child);
    }
    return out;
  };

  // frame -> {stable, cand, since}: its picture's settled size, and a new one until it settles
  // (while the phone turns, the window passes through other sizes for a moment).
  const SETTLE_MS = 1200;
  const last = new WeakMap();
  let turned = 0;
  const timer = setInterval(() => {
    try {
      let found = null;
      for (const f of FS.frames ?? []) {
        const c = f?.activePage?.size?.latestContentSize;
        if (!c?.unWidth || !c?.unHeight || f.docking?.dockLocation !== WORLD) continue;
        const cur = { w: c.unWidth, h: c.unHeight }, t = Date.now();
        const st = last.get(f) ?? { stable: cur, cand: cur, since: t };
        last.set(f, st);
        if (cur.w !== st.cand.w || cur.h !== st.cand.h) { st.cand = cur; st.since = t; }
        if (t - st.since < SETTLE_MS || (st.cand.w === st.stable.w && st.cand.h === st.stable.h)) continue;
        const was = st.stable, now = st.cand;
        st.stable = now;
        // A turn: upright <-> sideways, the same shape turned (aspect ratios within 5% of inverse).
        const turnedShape = (was.w > was.h) !== (now.w > now.h) &&
                            Math.abs((was.w / was.h) * (now.w / now.h) - 1) < 0.05;
        if (!turnedShape) continue;
        found ??= movers();
        const s = found.get(f), xf = s?.state?.xfTransform;
        if (!xf || f.docking.beingDragged) continue;
        // The width (in metres) stays: scale so the long side does instead.
        const k = Math.max(1, was.h / was.w) / Math.max(1, now.h / now.w);
        const sc = xf.scale ?? { x: 1, y: 1, z: 1 };
        s.setState({ xfTransform: { ...xf, scale: { x: sc.x * k, y: sc.y * k, z: sc.z * k } } });
        turned++;
      }
    } catch (e) { /* the dashboard changed: leave it */ }
  }, 250);

  all[NAME] = { version: VERSION, stats: () => ({ turned }), stop: () => clearInterval(timer) };
  return 'patched';
})();
