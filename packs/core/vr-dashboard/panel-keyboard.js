// frame-tweaks panel-keyboard: pressing a Frame Tweaks panel in VR (Arrow Pad, Screen snip's
// narration panel) doesn't take Steam's keyboard away from the window you're typing in.
// Steam's keyboard follows the laser's focus, so a press on one of them (an overlay of its own, not
// a dashboard window) reopened it for that panel: what you typed next went to the panel, which
// types nothing, instead of the window, and the dashboard placed the keyboard "undocked", at a spot
// tied to where the dashboard first appeared (so it jumped, far once the dashboard had been moved).
// Arrow Pad can't type it on for you: the desktop's focused window needn't be the one you were
// typing in (it went to the KDE desktop in the dashboard instead of a floating window). So when the
// keyboard comes to a panel, this gives it straight back to the overlay it was open for, as that
// window's own keyboard button would, and what you type goes there as before. If that can't be done
// (that window is gone, or SteamVR keeps handing it to the panel), the keyboard stays with the
// panel, at least docked where it was. (Before 0.6.19: Arrow Pad's own arrowpad-keyboard, for it
// alone.)
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// requires: keyboard info events | RegisterForKeyboardInfoChangedEvents
// requires: the dashboard store | window.DashboardStore=
// requires: the docked keyboard's place | debugHostLocation:"Dashboard"
// requires: its keyboard info handler | onKeyboardInfoChanged(e){this.m_bKeyboardVisible=e.visible,this.m_bKeyboardDockedInDashboard=e.dockedInDashboard,this.m_sKeyboardOverlayKey=e.overlayKey,this.m_nKeyboardFlags=e.keyboardFlags}
// requires: opening it for an overlay | VRHTML.VROverlay.ShowKeyboardForOverlay(
// requires: closing it | VRHTML.VROverlay.HideKeyboard()
(() => {
  const NAME = 'panel-keyboard', VERSION = 1;
  // Frame Tweaks' own panels: their overlay keys start so (Arrow Pad's vroverlay.py KEY, Screen
  // snip's frame-tweaks.snip.narration.PID). None of them takes typing.
  const PANEL = 'frame-tweaks.';
  const panel = (key) => typeof key === 'string' && key.startsWith(PANEL);
  const KEYBOARD = 'valve.steam.gamepadui.keyboard';   // (it takes the focus too: not a window to type in)
  const NORMAL = 0, SINGLE_LINE = 0;           // EGamepadTextInputMode, EGamepadTextLineInputMode
  const AGAIN_MS = 300;                        // a panel has it again this soon after: SteamVR insists
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const store = window.DashboardStore;
  // SteamVR can't take back a callback registered with it: the first copy of this patch registers
  // one for good, which calls the injected version's fix (none while it's stopped).
  const hub = (window.__sftPanelKeyboard ??= { fix: null });
  if (!hub.registered) {
    hub.registered = true;
    VRHTML.RegisterForKeyboardInfoChangedEvents((info) => hub.fix?.(info));
  }
  let last = null;                             // {key, flags}: the overlay it was last open for, not a panel
  let gaveBack = 0;                            // when it last gave it back
  const atPanel = () => store.m_bKeyboardVisible && panel(store.m_sKeyboardOverlayKey);
  const dock = () => store.onKeyboardInfoChanged({
    visible: true, dockedInDashboard: true, overlayKey: store.m_sKeyboardOverlayKey, keyboardFlags: store.m_nKeyboardFlags });
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
      console.warn('[panel-keyboard] could not give the keyboard back', to.key, e);
      return false;
    }
  };
  const fix = (info) => {
    if (!info?.visible) return;
    if (info.overlayKey && !panel(info.overlayKey) && info.overlayKey !== KEYBOARD) {
      last = { key: info.overlayKey, flags: info.keyboardFlags };
      return;
    }
    if (!panel(info.overlayKey)) return;
    // After the dashboard's own handler has stored SteamVR's word (the same event), before it's
    // drawn.
    queueMicrotask(() => {
      if (hub.fix !== fix || !atPanel()) return;
      if (!giveBack() && !store.m_bKeyboardDockedInDashboard) dock();
    });
  };
  hub.fix = fix;
  if (store.m_bKeyboardVisible && store.m_sKeyboardOverlayKey && !panel(store.m_sKeyboardOverlayKey) &&
      store.m_sKeyboardOverlayKey !== KEYBOARD) {
    last = { key: store.m_sKeyboardOverlayKey, flags: store.m_nKeyboardFlags };   // (open right now)
  }
  if (atPanel() && !store.m_bKeyboardDockedInDashboard) dock();
  all[NAME] = {
    version: VERSION,
    stop: () => {
      if (hub.fix === fix) hub.fix = null;
      if (atPanel() && store.m_bKeyboardDockedInDashboard) {       // back where SteamVR puts it
        store.onKeyboardInfoChanged({ visible: true, dockedInDashboard: false, overlayKey: store.m_sKeyboardOverlayKey,
                                      keyboardFlags: store.m_nKeyboardFlags });
      }
    },
  };
  return 'patched';
})()
