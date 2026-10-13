// steam-frame-tweaks phone-rotate: an upright floating window (the Android Mirror) comes up at a
// sensible size, and turning it (the phone sideways and back) just turns it.
// SteamVR starts every floating window as wide as a standard one whatever its shape, so an upright
// phone came up over 2 m tall; and it keeps a window's width when its shape changes, so turning
// the phone sideways shrank it to a strip. For a floating window that has been upright, this sets
// the panel height the dashboard's own override uses (size.mainPanelHeightOverride, as theater
// mode does), so its long side is LONG_M: upright, LONG_M tall; sideways, LONG_M wide. Resizing
// it with its handle still works on top of that.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// requires: the frame's panel height override | resize_main_panel_height:g.size.mainPanelHeightOverride
// requires: override from component props | null!=this.componentProps.forcedUniformDashboardHeight
// requires: component props from the frame's props | get componentProps(){
// requires: overlay picture size | GetOverlayMouseScale(
// requires: EDockLocation.World = 4 | e[e.World=4]="World"
(() => {
  const NAME = 'phone-rotate', VERSION = 6, WORLD = 4;
  const LONG_M = 0.8;                  // long side of a turned window, metres (a standard one: 0.98 wide)
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore;
  if (!FS?.frames) return 'not patched: dashboard objects missing';

  // frame -> panel height (local units) for its size component's override. Each window's size
  // component holds its componentProps as a MobX computed value (made from the class's getter
  // when the window was created): wrap that value's derivation, per window.
  const heights = new WeakMap();
  const wrapped = new Map();           // size component -> its original derivation (for stop)
  const wrap = (f) => {
    const size = f.size;
    if (!size || wrapped.has(size)) return true;
    const admin = Object.getOwnPropertySymbols(size).map((k) => size[k]).find((v) => v?.values_?.get);
    const cv = admin?.values_.get('componentProps');
    if (typeof cv?.derivation !== 'function') return false;
    const orig = cv.derivation;
    cv.derivation = function () {
      const p = orig.call(this);
      const h = heights.get(f);
      return h === undefined ? p : { ...p, forcedUniformDashboardHeight: h };
    };
    wrapped.set(size, { cv, orig });
    return true;
  };
  // The override is computed from the frame's (observable) props: a fresh copy makes it look again.
  const nudge = (f) => { try { f.props = { ...f.props }; } catch (e) { /* changed */ } };

  // The window's picture size, from its overlay (the page's latestContentSize is only read again
  // when something else changes, so it can stay at the old shape after the phone turns).
  const pictureSize = (f) => {
    try {
      const m = VRHTML.VROverlay.GetOverlayMouseScale(VRHTML.VROverlay.FindOverlay(f.activePage.summonOverlayKey));
      if (m?.x > 0 && m?.y > 0) return { unWidth: m.x, unHeight: m.y };
    } catch (e) { /* no overlay */ }
    return f.activePage?.size?.latestContentSize;
  };
  const upright = new WeakSet();       // floating windows seen upright: these get the override
  let set = 0;
  const timer = setInterval(() => {
    try {
      for (const f of FS.frames ?? []) {
        if (!f?.size) continue;
        const c = f.docking?.dockLocation === WORLD ? pictureSize(f) : null;
        if (f.docking?.dockLocation !== WORLD || !c?.unWidth || !c?.unHeight) {
          if (heights.has(f)) { heights.delete(f); nudge(f); }       // docked: the dashboard's size
          upright.delete(f);
          continue;
        }
        // Every shape at once, also the ones it passes through while turning: a moment of
        // in-between size beats a second of the wrong one.
        const s = { w: c.unWidth, h: c.unHeight };
        if (s.h > s.w) upright.add(f);
        if (!upright.has(f)) continue;
        const perMetre = 1 / (f.activePage.size.mainPanelWorldScaleIgnoringResizing || 1);
        const want = LONG_M * Math.min(1, s.h / s.w) * perMetre;
        const have = heights.get(f);
        if ((have === undefined || Math.abs(have - want) > want * 0.01) && wrap(f)) {
          heights.set(f, want);
          nudge(f);
          set++;
        }
      }
    } catch (e) { /* the dashboard changed: leave it */ }
  }, 50);

  all[NAME] = {
    version: VERSION,
    stats: () => ({ set }),
    stop: () => {
      clearInterval(timer);
      for (const { cv, orig } of wrapped.values()) cv.derivation = orig;
      for (const f of FS.frames ?? []) if (heights.has(f)) nudge(f);
    },
  };
  return 'patched';
})();
