// frame-tweaks arrowpad-keyboard: Steam's keyboard stays put when you press Arrow Pad.
// Steam's keyboard follows the laser's focus, so a press on Arrow Pad (an overlay of its own, not a
// dashboard window) reopens it for the pad. The dashboard then places it "undocked": at a spot tied
// to where the dashboard first appeared, not where you moved it, and tilted differently, so it
// jumped (far, once the dashboard had been moved). This tells the dashboard the keyboard is docked
// for Arrow Pad too: it stays where it is for the dashboard's windows, and moves with the dashboard.
// Only its place changes; what's typed still goes to the pad, which types it on the desktop.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// requires: keyboard info events | RegisterForKeyboardInfoChangedEvents
// requires: the dashboard store | window.DashboardStore=
// requires: the docked keyboard's place | debugHostLocation:"Dashboard"
// requires: its keyboard info handler | onKeyboardInfoChanged(e){this.m_bKeyboardVisible=e.visible,this.m_bKeyboardDockedInDashboard=e.dockedInDashboard,this.m_sKeyboardOverlayKey=e.overlayKey,this.m_nKeyboardFlags=e.keyboardFlags}
(() => {
  const NAME = 'arrowpad-keyboard', VERSION = 1;
  const PAD = 'frame-tweaks.arrowpad';         // the VR pad's overlay key (vroverlay.py KEY)
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const store = window.DashboardStore;
  // SteamVR can't take back a callback registered with it: the first copy of this patch registers
  // one for good, which calls the injected version's fix (none while it's stopped).
  const hub = (window.__sftArrowpadKeyboard ??= { fix: null });
  if (!hub.registered) {
    hub.registered = true;
    VRHTML.RegisterForKeyboardInfoChangedEvents((info) => hub.fix?.(info));
  }
  const ours = () => store.m_bKeyboardVisible && store.m_sKeyboardOverlayKey === PAD;
  const dock = () => store.onKeyboardInfoChanged({
    visible: true, dockedInDashboard: true, overlayKey: PAD, keyboardFlags: store.m_nKeyboardFlags });
  const fix = (info) => {
    if (!info?.visible || info.overlayKey !== PAD || info.dockedInDashboard) return;
    // After the dashboard's own handler has stored SteamVR's word (the same event), before it's
    // drawn: the keyboard never shows at the other spot.
    queueMicrotask(() => {
      if (hub.fix === fix && ours() && !store.m_bKeyboardDockedInDashboard) dock();
    });
  };
  hub.fix = fix;
  if (ours() && !store.m_bKeyboardDockedInDashboard) dock();      // (open for the pad right now)
  all[NAME] = {
    version: VERSION,
    stop: () => {
      if (hub.fix === fix) hub.fix = null;
      if (ours() && store.m_bKeyboardDockedInDashboard) {          // back where SteamVR puts it
        store.onKeyboardInfoChanged({ visible: true, dockedInDashboard: false, overlayKey: PAD,
                                      keyboardFlags: store.m_nKeyboardFlags });
      }
    },
  };
  return 'patched';
})()
