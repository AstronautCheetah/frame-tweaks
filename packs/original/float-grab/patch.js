// frame-tweaks float-grab: "Float in World" also picks the window up, as grabbing the bar
// under it does, so you place it in one go. It's let go by your next click, or by releasing the
// trigger if you're still holding the click that floated it. While it's held, and briefly after,
// "Return to Dashboard" (the button that replaced Float in World under the laser) is ignored for
// that window, so the click that puts it down can't dock it again.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard. It calls the dashboard's
// own drag (UndockedOverlay.startFloatingWindowMove / endFloatingWindowMove), with the controller
// that pressed the button (the dashboard's primary device), encoded the way SteamVR's laser
// mouse events encode it (NumLock = left hand, NumLock + CapsLock = right hand).
// requires: the Float in World button | "#FloatInWorld"
// requires: it sets the dock | docking.SetDockLocation(
// requires: UndockedOverlay.startFloatingWindowMove | startFloatingWindowMove(e){
// requires: UndockedOverlay.endFloatingWindowMove | endFloatingWindowMove(){
// requires: the drag ends on mouseup | window.addEventListener("mouseup",this.endFloatingWindowMove)
// requires: hand from mouse modifiers (CapsLock) | getModifierState("CapsLock")&&(
// requires: hand from mouse modifiers (NumLock) | getModifierState("NumLock")&&(
// requires: EDockLocation.Dashboard = 1 | .Dashboard=1]="Dashboard"
// requires: EDockLocation.World = 4 | .World=4]="World"
(() => {
  const NAME = 'float-grab', VERSION = 3;
  const RELEASE_DEG = 2;            // trigger moved this far from where it was: a click ended or began
  const NO_REDOCK_MS = 1500;        // after putting it down, ignore Return to Dashboard this long
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore, V = window.VRHTML, L = window.__sftLib;
  if (!FS || !V?.VROverlay?.GetPrimaryDashboardDevice) return 'not patched: dashboard objects missing';
  if (!L) return 'not patched: the dashboard helpers (vr-dashboard/lib.js) are missing';
  const DASH = L.DOCK.Dashboard, WORLD = L.DOCK.World;

  // The React component that floats frame f (exists once the window is in the world).
  const mover = (f) => L.walk((fb) => typeof fb.stateNode?.startFloatingWindowMove === 'function' &&
                                     fb.stateNode.props?.frame === f)?.stateNode ?? null;
  const hand = () => {           // 'left' / 'right' for the controller pointing at the dashboard
    const role = V.VRSystem.GetControllerRoleForTrackedDeviceIndex(V.VROverlay.GetPrimaryDashboardDevice());
    return role === 1 ? 'left' : role === 2 ? 'right' : null;
  };
  const trigger = (h) => {       // the trigger's current pose on that controller, or null
    const path = `/user/hand/${h}`;
    const rm = V.VRProperties.GetStringProperty(path, 1003);          // RenderModelName_String
    const comp = rm && V.VRRenderModelsInternal.FindComponentForInputSource(rm, '/input/trigger');
    const st = comp && V.VRRenderModels.GetComponentStateForDevicePath(rm, comp, path);
    return st?.xfTrackingToComponentLocal ?? null;
  };
  const degreesBetween = (a, b) => {   // rotation between two poses ({rotation: quaternion})
    const p = a.rotation, q = b.rotation;
    const dot = Math.abs(p.w * q.w + p.x * q.x + p.y * q.y + p.z * q.z);
    return (2 * Math.acos(Math.min(1, dot)) * 180) / Math.PI;
  };

  let grabbed = 0, active = null;     // active: {frame, mover, hand, trigger0, timer}
  let noRedock = { frame: null, until: 0 };
  const onPageClick = () => finish();  // a laser click on the dashboard page itself
  const finish = () => {
    if (!active) return;
    clearInterval(active.timer);
    window.removeEventListener('mousedown', onPageClick, true);
    const a = active;
    active = null;
    noRedock = { frame: a.frame, until: Date.now() + NO_REDOCK_MS };
    try { if (a.frame.docking.beingDragged) a.mover.endFloatingWindowMove(); } catch (e) { /* changed */ }
  };
  const pickUp = (f, h) => {
    let tries = 0;
    const wait = setInterval(() => {                    // the floating component mounts shortly after
      const s = mover(f);
      if (!s?.state?.xfTransform && ++tries < 25) return;
      clearInterval(wait);
      if (!s || f.docking.dockLocation !== WORLD || f.docking.beingDragged) return;
      const ev = { getModifierState: (k) => k === 'NumLock' || (h === 'right' && k === 'CapsLock'),
                   preventDefault() {}, stopPropagation() {} };
      s.startFloatingWindowMove(ev);
      grabbed++;
      const t0 = trigger(h);
      window.addEventListener('mousedown', onPageClick, true);
      active = { frame: f, mover: s, hand: h, trigger0: t0, timer: setInterval(() => {
        try {
          if (!f.docking.beingDragged) return finish();           // ended by a click (mouseup)
          const t = trigger(h);
          if (t0 && t && degreesBetween(t0, t) >= RELEASE_DEG) finish();   // trigger let go / pressed
        } catch (e) { finish(); }
      }, 15) };
    }, 40);
  };

  // Wrap each window's SetDockLocation once: Float in World = dashboard -> world, not mid-drag.
  const wrapped = new WeakSet();
  const wrapAll = () => {
    for (const f of FS.frames ?? []) {
      const d = f?.docking;
      if (!d || wrapped.has(d) || typeof d.SetDockLocation !== 'function') continue;
      const orig = d.SetDockLocation;
      d.SetDockLocation = function (loc, ...rest) {
        const from = d.dockLocation, dragging = d.beingDragged;
        if (loc === DASH && from === WORLD &&
            ((active && active.frame === f) || (noRedock.frame === f && Date.now() < noRedock.until))) {
          finish();
          return undefined;                     // the put-down click hit Return to Dashboard: ignore it
        }
        const r = orig.call(this, loc, ...rest);
        try {
          if (from === DASH && loc === WORLD && !dragging && !active) {
            const h = hand();
            if (h) pickUp(f, h);
          }
        } catch (e) { /* dashboard changed: leave it */ }
        return r;
      };
      d.__sftOrigSetDock = { orig, own: Object.prototype.hasOwnProperty.call(d, 'SetDockLocation') };
      wrapped.add(d);
    }
  };
  wrapAll();
  const timer = setInterval(() => { try { wrapAll(); } catch (e) {} }, 500);
  all[NAME] = {
    version: VERSION,
    stop: () => {
      clearInterval(timer);
      finish();
      for (const f of FS.frames ?? []) {
        const d = f?.docking, saved = d?.__sftOrigSetDock;
        if (!saved) continue;
        if (saved.own) d.SetDockLocation = saved.orig;
        else delete d.SetDockLocation;                   // back to the class's own method
        delete d.__sftOrigSetDock;
      }
    },
    get grabbed() { return grabbed; },
  };
  return 'patched';
})()
