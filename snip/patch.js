// steam-frame-tweaks snip-float: a screen snip of a floating window opens where that window floats,
// not in the dashboard. The selection window's title is "Screen snip · <snipped window's title>"
// (frame-snip sets it); when that window floats in the world, the selection window is floated
// too and given the same place (the floating component's own transform state), so you draw the
// rectangle right over it. Snips of the desktop or other docked windows are left in the dashboard.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// requires: UndockedOverlay.startFloatingWindowMove | startFloatingWindowMove(e){
// requires: floating transform state | this.setState({xfTransform:r})
// requires: a floated window is nudged | SetJustFloatedFromDashboard(e==o.yWq.World)
// requires: EDockLocation.Dashboard = 1 | e[e.Dashboard=1]="Dashboard"
// requires: EDockLocation.World = 4 | e[e.World=4]="World"
(() => {
  const NAME = 'snip-float', VERSION = 1, DASH = 1, WORLD = 4;
  const PREFIX = 'Screen snip · ';
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore;
  if (!FS) return 'not patched: dashboard objects missing';

  // The React component that floats frame f (exists once the window is in the world).
  const mover = (f) => {
    const rootEl = document.getElementById('root') ?? document.body.firstElementChild;
    const key = rootEl && Object.keys(rootEl).find((k) => k.startsWith('__reactContainer$'));
    if (!key) return null;
    const stack = [rootEl[key]];
    let n = 0;
    while (stack.length && n++ < 50000) {
      const fb = stack.pop();
      const s = fb.stateNode;
      if (s && typeof s.startFloatingWindowMove === 'function' && s.props?.frame === f) return s;
      if (fb.sibling) stack.push(fb.sibling);
      if (fb.child) stack.push(fb.child);
    }
    return null;
  };

  let placed = 0;
  const seen = new WeakSet();
  const place = (snip, source) => {
    const from = mover(source);
    const xf = from?.state?.xfTransform;
    if (!xf) return;
    snip.docking.SetDockLocation(WORLD);
    snip.docking.SetJustFloatedFromDashboard(false);   // (no "just floated" nudge toward you)
    // Its component mounts, then sets a starting place of its own (asynchronously): set ours a
    // few times over the first second so it wins.
    let n = 0;
    const t = setInterval(() => {
      const s = mover(snip);
      if (s && snip.docking.dockLocation === WORLD && !snip.docking.beingDragged) {
        s.setState({ xfTransform: xf, sParentDevice: from.state.sParentDevice });
      }
      if (++n >= 10) { clearInterval(t); placed++; }
    }, 100);
  };
  const timer = setInterval(() => {
    try {
      for (const f of FS.frames ?? []) {
        if (!f || seen.has(f) || !(f.title ?? '').startsWith(PREFIX)) continue;
        seen.add(f);
        const title = f.title.slice(PREFIX.length);
        const source = (FS.frames ?? []).find((g) => g !== f && g?.title === title);
        if (source?.docking?.dockLocation === WORLD && f.docking?.dockLocation === DASH) place(f, source);
      }
    } catch (e) { /* the dashboard changed: leave it */ }
  }, 150);

  all[NAME] = {
    version: VERSION,
    stats: () => ({ placed }),
    stop: () => clearInterval(timer),
  };
  return 'patched';
})();
