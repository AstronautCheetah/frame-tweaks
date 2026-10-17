// frame-tweaks arrowpad-keyboard: pressing Arrow Pad doesn't take Steam's keyboard away from the
// window you're typing in.
// Steam's keyboard follows the laser's focus, so a press on Arrow Pad (an overlay of its own, not a
// dashboard window) reopened it for the pad: what you typed next went to the pad instead of the
// window, and the dashboard placed the keyboard "undocked", at a spot tied to where the dashboard
// first appeared (so it jumped, far once the dashboard had been moved). The pad can't type it on
// for you: the desktop's focused window needn't be the one you were typing in (it went to the KDE
// desktop in the dashboard instead of a floating window). So when the keyboard comes to the pad,
// this gives it straight back to the overlay it was open for, as that window's own keyboard button
// would, and what you type goes there as before. If that can't be done (that window is gone, or
// SteamVR keeps handing it to the pad), the keyboard stays with the pad, at least docked where it
// was; the pad types nothing it gets.
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// requires: keyboard info events | RegisterForKeyboardInfoChangedEvents
// requires: the dashboard store | window.DashboardStore=
// requires: the docked keyboard's place | debugHostLocation:"Dashboard"
// requires: its keyboard info handler | onKeyboardInfoChanged(e){this.m_bKeyboardVisible=e.visible,this.m_bKeyboardDockedInDashboard=e.dockedInDashboard,this.m_sKeyboardOverlayKey=e.overlayKey,this.m_nKeyboardFlags=e.keyboardFlags}
// requires: opening it for an overlay | VRHTML.VROverlay.ShowKeyboardForOverlay(
// requires: closing it | VRHTML.VROverlay.HideKeyboard()
(() => {
  const NAME = 'arrowpad-keyboard', VERSION = 2;
  const PAD = 'frame-tweaks.arrowpad';         // the VR pad's overlay key (vroverlay.py KEY)
  const KEYBOARD = 'valve.steam.gamepadui.keyboard';   // (it takes the focus too: not a window to type in)
  const NORMAL = 0, SINGLE_LINE = 0;           // EGamepadTextInputMode, EGamepadTextLineInputMode
  const AGAIN_MS = 300;                        // the pad has it again this soon after: SteamVR insists
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
  let last = null;                             // {key, flags}: the overlay it was last open for, not the pad
  let gaveBack = 0;                            // when it last gave it back
  const ours = () => store.m_bKeyboardVisible && store.m_sKeyboardOverlayKey === PAD;
  const dock = () => store.onKeyboardInfoChanged({
    visible: true, dockedInDashboard: true, overlayKey: PAD, keyboardFlags: store.m_nKeyboardFlags });
  const exists = (key) => {
    try { return !!VRHTML.VROverlay.FindOverlay(key); } catch (e) { return false; }
  };
  const giveBack = () => {
    const to = last;
    if (!to || !exists(to.key) || Date.now() - gaveBack < AGAIN_MS) return false;
    try {
      VRHTML.VROverlay.HideKeyboard();
      VRHTML.VROverlay.ShowKeyboardForOverlay(to.key, NORMAL, SINGLE_LINE, to.flags, '', 1024, '', 0);
      gaveBack = Date.now();
      return true;
    } catch (e) {
      console.warn('[arrowpad-keyboard] could not give the keyboard back', to.key, e);
      return false;
    }
  };
  const fix = (info) => {
    if (!info?.visible) return;
    if (info.overlayKey && info.overlayKey !== PAD && info.overlayKey !== KEYBOARD) {
      last = { key: info.overlayKey, flags: info.keyboardFlags };
      return;
    }
    if (info.overlayKey !== PAD) return;
    // After the dashboard's own handler has stored SteamVR's word (the same event), before it's
    // drawn.
    queueMicrotask(() => {
      if (hub.fix !== fix || !ours()) return;
      if (!giveBack() && !store.m_bKeyboardDockedInDashboard) dock();
    });
  };
  hub.fix = fix;
  if (store.m_bKeyboardVisible && store.m_sKeyboardOverlayKey && store.m_sKeyboardOverlayKey !== PAD &&
      store.m_sKeyboardOverlayKey !== KEYBOARD) {
    last = { key: store.m_sKeyboardOverlayKey, flags: store.m_nKeyboardFlags };   // (open right now)
  }
  if (ours() && !store.m_bKeyboardDockedInDashboard) dock();
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
