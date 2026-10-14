// frame-tweaks curvature: windows floated into the world start curved.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard's sft-dashboard.
// Stock rule (systemui's `curvature` frame component): shouldCurve = the "Toggle Curvature"
// override if set, else curved in the dashboard, theater per setting, flat in the world.
// For a world window with no override we press the stock toggle once, so it stays the
// user's choice: toggling it flat sticks; a dock change clears the override (stock) and
// the next world placement curves again. Idea from lhns/steam-frame-nix's window-curvature.
// requires: the curvature component | componentName="curvature"
// requires: ToggleCurvature() | ToggleCurvature(){this.m_bCurveOverride=!this.shouldCurve}
// requires: world windows flat by default | .Curved;default:return!1}
// requires: EDockLocation.World = 4 | .World=4]="World"
(() => {
  const NAME = 'curvature', VERSION = 2, WORLD = 4;   // EDockLocation.World
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  window.__sftCurvature?.stop?.();                    // injected by older versions
  delete window.__sftCurvature;
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
  all[NAME] = { version: VERSION, stop: () => clearInterval(timer), get curved() { return curved; } };
  return 'patched';
})()
