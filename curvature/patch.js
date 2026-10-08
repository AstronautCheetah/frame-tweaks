// steam-frame-tweaks curvature: windows floated into the world start curved.
// Injected into SteamVR's dashboard page ("systemui") over its local DevTools port.
// Stock rule (systemui's `curvature` frame component): shouldCurve = the "Toggle Curvature"
// override if set, else curved in the dashboard, theater per setting, flat in the world.
// For a world window with no override we press the stock toggle once, so it stays the
// user's choice: toggling it flat sticks; a dock change clears the override (stock) and
// the next world placement curves again. Idea from lhns/steam-frame-nix's window-curvature.
(() => {
  const VERSION = 1, WORLD = 4;                   // EDockLocation.World
  const prev = window.__sftCurvature;
  if (prev?.version === VERSION) return 'already patched';
  prev?.stop?.();
  const FS = window.FrameStore;
  if (!FS) return 'not patched: window.FrameStore missing';
  let curved = 0;
  const tick = () => {
    for (const f of FS.frames ?? []) {
      const c = f?.curvature;
      if (!c || typeof c.ToggleCurvature !== 'function') continue;
      if (f.docking?.dockLocation === WORLD && c.m_bCurveOverride === undefined && !c.shouldCurve) {
        c.ToggleCurvature();
        curved++;
      }
    }
  };
  const timer = setInterval(() => { try { tick(); } catch (e) { /* dashboard changed: stay idle */ } }, 400);
  window.__sftCurvature = { version: VERSION, stop: () => clearInterval(timer), get curved() { return curved; } };
  return 'patched';
})()
