// frame-tweaks dashboard helpers: what the patches share (window.__sftLib). sft-dashboard injects
// this before the patches, each time it injects them. Only plumbing for finding and drawing
// things in SteamVR's dashboard page; no behaviour of its own.
// requires: window.Dashboard | window.Dashboard=
// requires: overlay picture size | GetOverlayMouseScale(
// requires: EDockLocation.Dashboard = 1 | .Dashboard=1]="Dashboard"
// requires: EDockLocation.World = 4 | .World=4]="World"
(() => {
  const VERSION = 1;
  if (window.__sftLib?.version === VERSION) return 'already loaded';
  const DOCK = { Dashboard: 1, World: 4 };
  // Panel anchors, for GetPanelAnchorID (a window has no Center anchor of its own).
  const ANCHOR = { TopCenter: 1, CenterLeft: 3, Center: 4, CenterRight: 5, BottomCenter: 7 };

  // Walk the dashboard's rendered React fibers; the first fiber visit() accepts, or null.
  const walk = (visit, limit = 50000) => {
    const rootEl = document.getElementById('root') ?? document.body.firstElementChild;
    const key = rootEl && Object.keys(rootEl).find((k) => k.startsWith('__reactContainer$'));
    if (!key) return null;
    const stack = [rootEl[key]];
    for (let n = 0; stack.length && n < limit; n++) {
      const fb = stack.pop();
      if (visit(fb)) return fb;
      if (fb.sibling) stack.push(fb.sibling);
      if (fb.child) stack.push(fb.child);
    }
    return null;
  };

  // The dashboard's scene-graph panel and transform components, found among its rendered fibers.
  let PANEL = null, XFORM = null;
  const components = () => {
    if (!(PANEL && XFORM)) {
      walk((fb) => {
        const p = fb.memoizedProps;
        if (p && typeof p === 'object' && typeof fb.type === 'function') {
          if (!PANEL && 'debug_name' in p && 'width' in p && 'interactive' in p) PANEL = fb.type;
          if (!XFORM && 'parent_id' in p && 'translation' in p && !('width' in p)) XFORM = fb.type;
        }
        return PANEL && XFORM;
      });
    }
    return PANEL && XFORM ? { PANEL, XFORM } : null;
  };

  // React elements, made like the dashboard's own (copied from one of its elements: the page
  // has no global React to call createElement on).
  let SAMPLE = null;
  const el = (type, props, ...children) => {
    const e = Object.assign({}, SAMPLE, { type, key: props?.key ?? null,
      props: Object.assign({}, props, children.length ? { children: children.length === 1 ? children[0] : children } : {}) });
    if ('_store' in e) e._store = {};
    if ('ref' in e && !('ref' in (props ?? {}))) e.ref = null;
    return e;
  };

  // A window's picture size {w, h}, from its overlay (the page's own latestContentSize is only
  // read again when something else changes, so it can keep an old shape).
  const pictureSize = (page) => {
    try {
      const m = VRHTML.VROverlay.GetOverlayMouseScale(VRHTML.VROverlay.FindOverlay(page.summonOverlayKey));
      if (m?.x > 0 && m?.y > 0) return { w: m.x, h: m.y };
    } catch (e) { /* no overlay */ }
    const c = page?.size?.latestContentSize;
    return c?.unWidth > 0 && c?.unHeight > 0 ? { w: c.unWidth, h: c.unHeight } : null;
  };

  // memo(): a small cache, so a patch hands the dashboard the very same pieces while nothing
  // they show has changed (fresh copies, even identical ones, get sent to SteamVR again).
  const memo = (max = 40) => {
    const m = new Map();
    return (key, make) => {
      if (m.has(key)) return m.get(key);
      const v = make();
      m.set(key, v);
      if (m.size > max) m.delete(m.keys().next().value);
      return v;
    };
  };

  // Our pieces are drawn from the dashboard's one shared page (about 1860 x 2048). Placed after
  // its own content they moved whenever that changed size, which showed as jitter, and tall ones
  // ran off the page: each patch gets a fixed corner of its own at the bottom.
  const area = (side) => ({ position: 'absolute', bottom: '0px', width: '920px', [side]: '0px',
                            textAlign: side === 'right' ? 'right' : 'left' });

  // mount(key, render, side): draw render() (an array of pieces, or null) as the last child of
  // the dashboard app, redrawn every `every` ms and on redraw(); in the page corner `side`. Puts
  // itself back if another patch's stop() drops it. Returns {redraw, stop}.
  const mount = (key, render, side, every = 500) => {
    const D = window.Dashboard;
    const Base = D && Object.getPrototypeOf(D.constructor);
    if (!Base?.prototype?.isReactComponent) return null;
    const app = walk((fb) => fb.stateNode && typeof fb.stateNode.toggleDebugPointer === 'function')?.stateNode;
    if (!app) return null;
    let on = true, mounted = 0, inst = null;
    class Holder extends Base {
      componentDidMount() { mounted++; inst = this; this.timer = setInterval(() => { try { this.forceUpdate(); } catch (e) {} }, every); }
      componentWillUnmount() { mounted--; if (inst === this) inst = null; clearInterval(this.timer); }
      render() {
        try {
          if (!on || !components()) return null;
          const parts = (render() ?? []).filter(Boolean);
          return parts.length ? el('div', { key: `${key}-area`, style: area(side) }, ...parts) : null;
        } catch (e) { return null; }
      }
    }
    const attach = () => {
      const below = app.render;
      app.render = function (...args) {
        const tree = below.apply(this, args);
        const kids = tree?.props?.children;
        if (!on || !tree || typeof tree !== 'object' || !Array.isArray(kids)) return tree;
        SAMPLE ??= tree;
        return Object.assign({}, tree, { props: Object.assign({}, tree.props, { children: [...kids, el(Holder, { key })] }) });
      };
      try { app.forceUpdate(); } catch (e) {}
    };
    attach();
    const guard = setInterval(() => { if (on && !mounted) attach(); }, 2000);
    return {
      redraw: () => { try { inst?.forceUpdate(); } catch (e) {} },
      // (stays in the render chain, passing straight through: unwrapping could drop another's)
      stop: () => { on = false; clearInterval(guard); try { app.forceUpdate(); } catch (e) {} },
    };
  };

  // The dashboard's own controller haptics (what its buttons and sliders use): a tick on the
  // controller pointing at this overlay. Optional: does nothing if SteamVR's page API changes.
  const HAPTIC = { Enter: 1, Leave: 2, Snap: 3, Sliding: 4, SlidingEdge: 5 };
  const haptic = (effect) => {
    try {
      if (typeof VRHTML !== 'undefined' && VRHTML && VRHTML.VROverlay)
        VRHTML.VROverlay.TriggerOverlayHapticEffect(VRHTML.VROverlay.ThisOverlayHandle(), effect);
    } catch (e) {}
  };

  window.__sftLib = { version: VERSION, DOCK, ANCHOR, walk, components, el, pictureSize, memo, mount, HAPTIC, haptic };
  return 'loaded';
})()
