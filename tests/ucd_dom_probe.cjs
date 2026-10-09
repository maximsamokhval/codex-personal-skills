// Dependency-free DOM probe: runtime/layout invariants, not a browser screenshot.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fragment = fs.readFileSync(0, 'utf8');
const payload = fragment.match(/<script type="application\/json" id="([^"]+)">(.*?)<\/script>/s);
const script = [...fragment.matchAll(/<script>(.*?)<\/script>/gs)][0][1];
const model = JSON.parse(payload[2]);
const rootId = payload[1].replace(/-data$/, '');

for (const width of [320, 360, 736, 1024]) {
  class Element {
    constructor(tag) {
      this.tag = tag; this.attrs = {}; this.children = []; this.events = {};
      this.textContent = ''; this.hidden = false;
      this.classList = {toggle: () => {}};
    }
    setAttribute(key, value) { this.attrs[key] = value; }
    appendChild(child) { this.children.push(child); return child; }
    replaceChildren() { this.children = []; }
    getBoundingClientRect() { return {width}; }
    getContext() { return {measureText: s => ({width: Array.from(s).length * 9})}; }
    addEventListener(name, callback) { this.events[name] = callback; }
    querySelector(selector) {
      return all(this).find(e => Object.hasOwn(e.attrs, selector.slice(1, -1)));
    }
  }
  function all(el) { return [el, ...el.children.flatMap(all)]; }
  const root = new Element('div');
  const input = new Element('script'); input.textContent = payload[2];
  for (const attr of ['data-title','data-snapshot','data-legend','data-tabs','data-panels','data-notes-label','data-notes']) {
    const el = new Element('div'); el.setAttribute(attr, ''); root.appendChild(el);
  }
  const context = {
    document: {
      getElementById: id => id === rootId ? root : id === payload[1] ? input : null,
      createElement: tag => new Element(tag),
      createElementNS: (_ns, tag) => new Element(tag),
    },
    ResizeObserver: class { constructor(callback) { this.callback=callback; } observe() { this.callback(); } },
  };
  vm.runInNewContext(script, context);
  const elements = all(root);
  const svgs = elements.filter(e => e.tag === 'svg');
  assert.equal(svgs.length, model.views.length);
  for (const svg of svgs) {
    const [, , w, h] = svg.attrs.viewBox.split(' ').map(Number);
    assert.equal(w, width); assert.ok(Number.isFinite(h) && h > 0);
    const content = all(svg);
    const boundary = content.find(e => e.tag === 'rect');
    const bx = +boundary.attrs.x;
    const ellipses = content.filter(e => e.tag === 'ellipse');
    for (const ellipse of ellipses) {
      const {cx, cy, rx, ry} = Object.fromEntries(Object.entries(ellipse.attrs).map(([k,v]) => [k,+v]));
      assert.ok([cx,cy,rx,ry].every(Number.isFinite));
      assert.ok(cx-rx > bx && cx+rx < w && cy-ry > 8 && cy+ry < h-8);
      const group = content.find(e => e.children.includes(ellipse));
      const text = group.children.find(e => e.tag === 'text');
      let lineY = +text.attrs.y;
      for (const line of text.children) {
        lineY += +line.attrs.dy;
        const halfWidth = Array.from(line.textContent).length*9/2;
        const maxHalf = rx*Math.sqrt(1-((lineY-cy)/ry)**2);
        assert.ok(halfWidth < maxHalf, `ellipse label clipped at ${width}: ${line.textContent}`);
      }
    }
    const actorGroups = content.filter(e => e.attrs['data-actor-id']);
    assert.ok(actorGroups.every(e => +e.children[0].attrs.cx < bx));
    assert.ok(content.filter(e => e.attrs['data-association']).every(e => !e.attrs['marker-end']));
  }
  const tabs = elements.filter(e => e.attrs.role === 'tab');
  const panels = elements.filter(e => e.attrs.role === 'tabpanel');
  assert.equal(tabs.length, panels.length);
  tabs.forEach((tab, i) => {
    tab.events.click();
    panels.forEach((panel, j) => assert.equal(panel.hidden, i !== j));
    assert.equal(tab.attrs['aria-selected'], 'true');
  });
  const observed = elements.filter(e => e.attrs['data-case-id']).map(e => e.attrs['data-case-id']);
  assert.deepEqual(observed, model.views.flatMap(v => v.cases.map(c => c.id)));
}
process.stdout.write('UCD runtime, tab switching and geometry probes passed at 320..1024px.\n');
