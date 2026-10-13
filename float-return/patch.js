// steam-frame-tweaks float-return: after you float the window the dashboard is showing out into
// the world, the dashboard goes back (after 2.5 s) to the window it showed before, instead of
// leaving an empty space. Injected into SteamVR's dashboard page ("systemui") by vr-dashboard.
// It only switches the way a click on that window's dashboard button does (switchToFrameInternal).
// requires: window.Dashboard | window.Dashboard=
// requires: Dashboard.switchToFrameInternal() | switchToFrameInternal(e,t,r){
// requires: window.DashboardStore | window.DashboardStore=
// requires: DashboardStore.activeFrame | get activeFrame(){
// requires: EDockLocation.Dashboard = 1 | e[e.Dashboard=1]="Dashboard"
// requires: EDockLocation.World = 4 | e[e.World=4]="World"
(() => {
  const NAME = 'float-return', VERSION = 2, DASH = 1, WORLD = 4, DELAY_MS = 2500;
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore, DS = window.DashboardStore, D = window.Dashboard;
  if (!FS || !DS || typeof D?.switchToFrameInternal !== 'function') return 'not patched: dashboard objects missing';
  const dockOf = (id) => FS.GetFrame(id)?.docking?.dockLocation;
  let history = [];        // windows shown in the dashboard, most recent last (frame IDs)
  let last = null;         // what the dashboard showed on the previous check: {id, dock}
  let pending = null;      // {from: the floated window, at: when}
  let returned = 0;
  const tick = () => {
    const a = DS.activeFrame, id = a?.frameID, dock = a?.docking?.dockLocation;
    if (a && dock === DASH) {
      if (history[history.length - 1] !== id) {
        history = history.filter((x) => x !== id);
        history.push(id);
        if (history.length > 20) history.shift();
      }
      pending = null;
    } else if (last && last.dock === DASH && dockOf(last.id) === WORLD && (!a || id === last.id)) {
      pending ??= { from: last.id, at: Date.now() };     // the shown window was just floated out
    }
    if (pending) {
      if (a && id !== pending.from) {
        pending = null;                                   // you picked something else meanwhile
      } else if (dockOf(pending.from) !== WORLD) {
        pending = null;                                   // docked again
      } else if (Date.now() - pending.at >= DELAY_MS) {
        const prev = [...history].reverse().find((x) => x !== pending.from && dockOf(x) === DASH);
        pending = null;
        if (prev != null && D.switchToFrameInternal(FS.GetFrame(prev), undefined, 'sft-float-return')) returned++;
      }
    }
    last = a ? { id, dock } : last;
  };
  const timer = setInterval(() => { try { tick(); } catch (e) { /* dashboard changed: stay idle */ } }, 200);
  all[NAME] = { version: VERSION, stop: () => clearInterval(timer), get returned() { return returned; } };
  return 'patched';
})()
