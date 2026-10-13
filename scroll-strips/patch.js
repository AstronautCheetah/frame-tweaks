// steam-frame-tweaks scroll-strips: big scroll strips beside each floating window, easy to hit with
// the laser. Drag along a strip to scroll (like dragging a scroll bar); tap near either end to
// page. Scrolling goes to the window you last clicked (SteamVR gives the dashboard no way to
// scroll a particular window), through vr-dashboard's sftScroll binding (ydotool's mouse wheel).
// Injected into SteamVR's dashboard page ("systemui") by vr-dashboard. Settings:
// window.__sftPatchConfig["scroll-strips"] = {vertical: "right"|"left"|"off",
//   horizontal: "top"|"bottom"|"off", thickness: metres (local), gap: metres}.
// requires: UndockedOverlay.renderFloatingFrame | renderFloatingFrame(){
// requires: the grab handle panel | debug_name:"GrabHandle",origin:
// requires: frame panel height | latestMeasuredPanelLocalHeight
// requires: EDockLocation.World = 4 | e[e.World=4]="World"
(() => {
  const NAME = 'scroll-strips', VERSION = 1, WORLD = 4;
  const NOTCHES_PER_LENGTH = 40;     // a drag along the whole strip scrolls this many wheel notches
  const PAGE = 10;                   // notches for a tap near an end
  const all = (window.__sftPatches ??= {});
  if (all[NAME]?.version === VERSION) return 'already patched';
  all[NAME]?.stop?.();
  const FS = window.FrameStore;
  const cfg = () => ({ vertical: 'right', horizontal: 'top', thickness: 0.12, gap: 0.03,
                       ...(window.__sftPatchConfig?.[NAME] ?? {}) });

  const movers = () => {
    const rootEl = document.getElementById('root');
    const key = rootEl && Object.keys(rootEl).find((k) => k.startsWith('__reactContainer$'));
    const out = [], stack = key ? [rootEl[key]] : [];
    while (stack.length) {
      const fb = stack.pop();
      if (fb.stateNode && typeof fb.stateNode.renderFloatingFrame === 'function') out.push(fb.stateNode);
      if (fb.sibling) stack.push(fb.sibling);
      if (fb.child) stack.push(fb.child);
    }
    return out;
  };
  const found = movers();
  if (!found.length) return 'waiting: no floating window yet';
  const proto = Object.getPrototypeOf(found[0]);
  const orig = proto.renderFloatingFrame;

  // React elements are plain objects: make ours by copying the shape of one the dashboard made.
  let SAMPLE = null, PANEL = null, PANEL_ORIGIN = null, XFORM = null;
  const el = (type, props, ...children) => {
    const e = Object.assign({}, SAMPLE, { type, key: props?.key ?? null,
      props: Object.assign({}, props, children.length ? { children: children.length === 1 ? children[0] : children } : {}) });
    if ('_store' in e) e._store = {};
    return e;
  };
  const walk = (node, fn) => {
    if (!node || typeof node !== 'object') return;
    if (Array.isArray(node)) return node.forEach((n) => walk(n, fn));
    fn(node);
    walk(node.props?.children, fn);
  };
  const learn = (tree) => {             // the panel and transform components, from the stock tree
    if (PANEL) return true;
    let handle = null, xform = null;
    walk(tree, (n) => {
      if (n.props?.onMouseDown && n.props?.width === 350) handle = n;            // the grab handle
      if (!xform && n.props && 'parent_id' in n.props && 'translation' in n.props) xform = n;
    });
    if (!handle || !xform) return false;
    const inner = handle.type(handle.props);                                      // -> its panel
    if (!inner?.props || !('width' in inner.props)) return false;
    SAMPLE = tree; PANEL = inner.type; PANEL_ORIGIN = inner.props.origin; XFORM = xform.type;
    return true;
  };

  let drag = null;
  const send = (dx, dy) => { try { window.sftScroll?.(JSON.stringify({ dx, dy })); } catch (e) {} };
  const onMove = (ev) => {
    if (!drag) return;
    const pos = drag.axis === 'y' ? ev.clientY : ev.clientX;
    drag.moved = Math.max(drag.moved, Math.abs(pos - drag.start));
    const want = Math.trunc(((pos - drag.start) / drag.length) * NOTCHES_PER_LENGTH);
    const step = want - drag.sent;
    if (step) {
      drag.sent = want;
      // Scroll-bar sense: drag down (or right) scrolls down (or right). Wheel: +y is up.
      drag.axis === 'y' ? send(0, -step) : send(step, 0);
    }
  };
  const onUp = (ev) => {
    window.removeEventListener('mousemove', onMove, true);
    window.removeEventListener('mouseup', onUp, true);
    const d = drag; drag = null;
    if (!d || d.moved > d.length * 0.03) return;
    const at = (d.start - d.from) / d.length;                    // a tap: near an end pages
    if (at < 0.25) d.axis === 'y' ? send(0, PAGE) : send(-PAGE, 0);
    else if (at > 0.75) d.axis === 'y' ? send(0, -PAGE) : send(PAGE, 0);
  };
  const strip = (axis, length_m, thick_m) => {
    const px = 60, lenPx = Math.round(px * length_m / thick_m);
    const style = { width: `${axis === 'y' ? px : lenPx}px`, height: `${axis === 'y' ? lenPx : px}px`,
      background: 'rgba(40, 50, 62, 0.55)', borderRadius: `${px / 2}px`, boxSizing: 'border-box',
      border: '3px solid rgba(127, 178, 229, 0.55)' };
    return el(PANEL, { width: axis === 'y' ? thick_m : length_m, interactive: true, only_visible_with_laser: false,
      debug_name: `SftScroll${axis.toUpperCase()}`, origin: PANEL_ORIGIN, inputFocusParams: { bCanTakeKeyboardFocus: false },
      hide_lasermouse_when_clicking: false },
      el('div', { style, onMouseDown: (ev) => {
        const r = ev.currentTarget.getBoundingClientRect();
        drag = { axis, start: axis === 'y' ? ev.clientY : ev.clientX, from: axis === 'y' ? r.top : r.left,
                 length: axis === 'y' ? r.height : r.width, sent: 0, moved: 0 };
        window.addEventListener('mousemove', onMove, true);
        window.addEventListener('mouseup', onUp, true);
      } }));
  };

  proto.renderFloatingFrame = function () {
    const tree = orig.call(this);
    try {
      const f = this.props.frame, page = f?.activePage;
      const H = page?.size?.latestMeasuredPanelLocalHeight, c = page?.size?.latestContentSize;
      if (!H || !c?.unHeight || f.docking.dockLocation !== WORLD || !learn(tree)) return tree;
      const W = H * c.unWidth / c.unHeight, o = cfg(), t = o.thickness, g = o.gap;
      const extra = [];
      // The window panel's origin is its bottom centre (mainPanelOrigin for world windows).
      if (o.vertical !== 'off') {
        const x = (o.vertical === 'left' ? -1 : 1) * (W / 2 + g + t / 2);
        extra.push(el(XFORM, { key: 'sft-scroll-y', parent_id: this.m_sPushedOriginID, translation: { x, y: 0 } }, strip('y', H, t)));
      }
      if (o.horizontal !== 'off') {
        const y = o.horizontal === 'bottom' ? -(g + t) : H + g;
        extra.push(el(XFORM, { key: 'sft-scroll-x', parent_id: this.m_sPushedOriginID, translation: { x: 0, y } }, strip('x', W, t)));
      }
      let added = false;
      walk(tree, (n) => {                          // beside the window, inside its grab/push node
        if (added || !n.props || !('base_distance' in n.props)) return;
        const kids = n.props.children;
        n.props = Object.assign({}, n.props, { children: [...(Array.isArray(kids) ? kids : [kids]), ...extra] });
        added = true;
      });
    } catch (e) { /* dashboard changed: show it as stock */ }
    return tree;
  };
  const refresh = () => movers().forEach((m) => { try { m.forceUpdate(); } catch (e) {} });
  refresh();
  all[NAME] = { version: VERSION, stop: () => { proto.renderFloatingFrame = orig; refresh(); },
                configChanged: refresh };
  return 'patched';
})()
