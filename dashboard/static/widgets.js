/* Rencora Holo-Mat Widgets — greifbare schwebende Panels auf dem Tisch (Uhr, Timer, Notiz,
   Rechner). Ziehen an der Kopfzeile, Größe über die Ecke, Schließen per ✕. Position/Größe/Status
   werden pro Widget in localStorage gemerkt. Bedienung per Pointer-Events (Maus, Touch, projiziert).
   Engine Mark-LI/FatihMakes CC BY-NC. */
(function () {
  var KEY = 'rencora_widgets';
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { state = {}; }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} }

  var css = document.createElement('style');
  css.textContent =
    '.rw-panel{position:fixed;z-index:9000;min-width:150px;min-height:90px;background:rgba(4,10,20,.82);' +
    'border:1px solid var(--cy,#b06bff);border-radius:12px;color:var(--ink,#dbe9ff);' +
    'box-shadow:0 0 26px rgba(0,0,0,.5),inset 0 0 24px rgba(120,120,255,.06);display:flex;flex-direction:column;' +
    'font-family:system-ui,sans-serif;-webkit-backdrop-filter:blur(5px);backdrop-filter:blur(5px);overflow:hidden}' +
    '.rw-hd{display:flex;align-items:center;justify-content:space-between;padding:7px 10px;cursor:grab;' +
    'font:600 11px/1 system-ui;letter-spacing:2px;color:var(--cy,#b06bff);text-shadow:0 0 8px var(--cy,#b06bff);' +
    'border-bottom:1px solid rgba(120,120,255,.18);touch-action:none;user-select:none}' +
    '.rw-x{cursor:pointer;opacity:.7;font-size:14px;padding:0 2px}.rw-x:hover{opacity:1}' +
    '.rw-bd{flex:1;padding:10px;overflow:auto}' +
    '.rw-grip{position:absolute;right:0;bottom:0;width:16px;height:16px;cursor:nwse-resize;' +
    'background:linear-gradient(135deg,transparent 50%,var(--cy,#b06bff) 50%);opacity:.6;touch-action:none}' +
    '.rw-clock{font:700 34px/1.1 ui-monospace,monospace;color:#fff;text-align:center;text-shadow:0 0 14px var(--cy,#b06bff)}' +
    '.rw-date{text-align:center;font-size:12px;opacity:.7;margin-top:4px}' +
    '.rw-in{width:100%;background:rgba(0,0,0,.35);border:1px solid rgba(120,120,255,.3);border-radius:7px;' +
    'color:#fff;font:14px system-ui;padding:8px;box-sizing:border-box;outline:none}' +
    '.rw-note{width:100%;height:100%;min-height:70px;resize:none;background:transparent;border:0;color:var(--ink,#dbe9ff);' +
    'font:13px/1.5 system-ui;outline:none}' +
    '.rw-btn{background:rgba(120,120,255,.14);border:1px solid var(--cy,#b06bff);color:#fff;border-radius:7px;' +
    'padding:8px;font:14px system-ui;cursor:pointer}.rw-btn:hover{background:var(--cy,#b06bff);color:#02121f}' +
    '.rw-timer{font:700 30px/1 ui-monospace,monospace;color:#fff;text-align:center;margin-bottom:8px}' +
    '.rw-calc-scr{font:600 20px/1 ui-monospace,monospace;text-align:right;color:#fff;background:rgba(0,0,0,.4);' +
    'border-radius:7px;padding:10px;margin-bottom:6px;min-height:22px;overflow:hidden}' +
    '.rw-calc-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:5px}' +
    '.rw-dock{position:fixed;left:50%;bottom:14px;transform:translateX(-50%);z-index:9100;display:flex;gap:8px;' +
    'background:rgba(4,10,20,.7);border:1px solid var(--cy,#b06bff);border-radius:12px;padding:7px 10px;' +
    '-webkit-backdrop-filter:blur(5px);backdrop-filter:blur(5px)}' +
    '.rw-dock button{background:transparent;border:0;color:var(--cy,#b06bff);font:600 11px system-ui;letter-spacing:1px;' +
    'cursor:pointer;padding:4px 8px;border-radius:7px}.rw-dock button:hover{background:rgba(120,120,255,.18)}';
  (document.head || document.documentElement).appendChild(css);

  function drag(panel, handle) {
    var sx, sy, ox, oy, on = false;
    handle.addEventListener('pointerdown', function (e) {
      on = true; handle.setPointerCapture(e.pointerId); handle.style.cursor = 'grabbing';
      sx = e.clientX; sy = e.clientY; var r = panel.getBoundingClientRect(); ox = r.left; oy = r.top;
    });
    handle.addEventListener('pointermove', function (e) {
      if (!on) return;
      var x = Math.max(0, Math.min(innerWidth - 60, ox + e.clientX - sx));
      var y = Math.max(0, Math.min(innerHeight - 40, oy + e.clientY - sy));
      panel.style.left = x + 'px'; panel.style.top = y + 'px';
    });
    handle.addEventListener('pointerup', function (e) {
      on = false; handle.style.cursor = 'grab';
      var st = state[panel.dataset.wid] || (state[panel.dataset.wid] = {});
      st.x = parseInt(panel.style.left); st.y = parseInt(panel.style.top); save();
    });
  }
  function resize(panel, grip) {
    var sx, sy, ow, oh, on = false;
    grip.addEventListener('pointerdown', function (e) {
      on = true; grip.setPointerCapture(e.pointerId); e.stopPropagation();
      sx = e.clientX; sy = e.clientY; ow = panel.offsetWidth; oh = panel.offsetHeight;
    });
    grip.addEventListener('pointermove', function (e) {
      if (!on) return;
      panel.style.width = Math.max(150, ow + e.clientX - sx) + 'px';
      panel.style.height = Math.max(90, oh + e.clientY - sy) + 'px';
    });
    grip.addEventListener('pointerup', function () {
      on = false; var st = state[panel.dataset.wid] || (state[panel.dataset.wid] = {});
      st.w = panel.offsetWidth; st.h = panel.offsetHeight; save();
    });
  }

  var PANELS = {};
  function makePanel(id, title, build, def) {
    if (PANELS[id]) { PANELS[id].style.display = 'flex'; return PANELS[id]; }
    var st = state[id] || {};
    var IW = innerWidth || 1280, IH = innerHeight || 720;   // innerWidth can be 0 before layout
    var w = st.w || def.w, h = st.h || def.h;
    var x = (st.x != null ? st.x : def.x), y = (st.y != null ? st.y : def.y);
    // guard against off-screen defaults or stale saved coords
    if (!(x >= 0 && x <= IW - 60)) x = Math.max(20, IW - w - 24);
    if (!(y >= 0 && y <= IH - 40)) y = Math.max(70, Math.min(IH - h - 20, 90));
    var p = document.createElement('div'); p.className = 'rw-panel'; p.dataset.wid = id;
    p.style.left = x + 'px'; p.style.top = y + 'px';
    p.style.width = w + 'px'; p.style.height = h + 'px';
    var hd = document.createElement('div'); hd.className = 'rw-hd';
    hd.innerHTML = '<span>' + title + '</span>'; var x = document.createElement('span');
    x.className = 'rw-x'; x.textContent = '✕'; hd.appendChild(x);
    var bd = document.createElement('div'); bd.className = 'rw-bd';
    var grip = document.createElement('div'); grip.className = 'rw-grip';
    p.appendChild(hd); p.appendChild(bd); p.appendChild(grip);
    document.body.appendChild(p);
    build(bd);
    drag(p, hd); resize(p, grip);
    x.addEventListener('click', function () { p.style.display = 'none'; state[id] = state[id] || {}; state[id].open = false; save(); });
    PANELS[id] = p; state[id] = state[id] || {}; state[id].open = true; save();
    return p;
  }

  // ---- Widget builders ----
  function wClock(bd) {
    var t = document.createElement('div'); t.className = 'rw-clock';
    var d = document.createElement('div'); d.className = 'rw-date'; bd.appendChild(t); bd.appendChild(d);
    function tick() { var n = new Date();
      t.textContent = n.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      d.textContent = n.toLocaleDateString('de-DE', { weekday: 'long', day: '2-digit', month: 'long' }); }
    tick(); setInterval(tick, 1000);
  }
  function wTimer(bd) {
    var disp = document.createElement('div'); disp.className = 'rw-timer'; disp.textContent = '05:00';
    var inp = document.createElement('input'); inp.className = 'rw-in'; inp.type = 'number'; inp.value = '5';
    inp.style.marginBottom = '6px'; inp.min = '1';
    var row = document.createElement('div'); row.style.cssText = 'display:flex;gap:6px';
    var b1 = document.createElement('button'); b1.className = 'rw-btn'; b1.textContent = 'Start'; b1.style.flex = '1';
    var b2 = document.createElement('button'); b2.className = 'rw-btn'; b2.textContent = 'Stop'; b2.style.flex = '1';
    row.appendChild(b1); row.appendChild(b2);
    bd.appendChild(disp); bd.appendChild(inp); bd.appendChild(row);
    var left = 300, iv = null;
    function fmt(s) { var m = Math.floor(s / 60), r = s % 60; return (m < 10 ? '0' : '') + m + ':' + (r < 10 ? '0' : '') + r; }
    function render() { disp.textContent = fmt(Math.max(0, left)); }
    b1.onclick = function () { left = Math.max(1, parseInt(inp.value) || 5) * 60; render();
      clearInterval(iv); iv = setInterval(function () { left--; render();
        if (left <= 0) { clearInterval(iv); disp.style.color = '#ff5a7a'; disp.textContent = '00:00 ⏰'; } }, 1000); };
    b2.onclick = function () { clearInterval(iv); disp.style.color = '#fff'; };
    render();
  }
  function wNote(bd) {
    var ta = document.createElement('textarea'); ta.className = 'rw-note'; ta.placeholder = 'Notiz…';
    try { ta.value = localStorage.getItem('rencora_widget_note') || ''; } catch (e) {}
    ta.addEventListener('input', function () { try { localStorage.setItem('rencora_widget_note', ta.value); } catch (e) {} });
    bd.appendChild(ta);
  }
  function wCalc(bd) {
    var scr = document.createElement('div'); scr.className = 'rw-calc-scr'; scr.textContent = '0';
    var grid = document.createElement('div'); grid.className = 'rw-calc-grid';
    bd.appendChild(scr); bd.appendChild(grid);
    var expr = '';
    var keys = ['7', '8', '9', '/', '4', '5', '6', '*', '1', '2', '3', '-', '0', '.', '=', '+', 'C'];
    keys.forEach(function (k) {
      var b = document.createElement('button'); b.className = 'rw-btn'; b.textContent = k;
      if (k === 'C') b.style.gridColumn = 'span 4';
      b.onclick = function () {
        if (k === 'C') { expr = ''; scr.textContent = '0'; return; }
        if (k === '=') { try { expr = String(Function('"use strict";return (' + expr.replace(/[^0-9.+\-*/() ]/g, '') + ')')()); }
          catch (e) { expr = 'Fehler'; } scr.textContent = expr; if (expr === 'Fehler') expr = ''; return; }
        expr += k; scr.textContent = expr;
      };
      grid.appendChild(b);
    });
  }

  var DEFS = {
    clock: { title: 'UHR', build: wClock, def: { x: 40, y: 90, w: 220, h: 130 } },
    timer: { title: 'TIMER', build: wTimer, def: { x: 40, y: 240, w: 200, h: 190 } },
    note:  { title: 'NOTIZ', build: wNote, def: { x: innerWidth - 260, y: 90, w: 230, h: 200 } },
    calc:  { title: 'RECHNER', build: wCalc, def: { x: innerWidth - 260, y: 310, w: 230, h: 300 } }
  };
  function toggle(id) {
    var p = PANELS[id];
    if (p && p.style.display !== 'none') { p.style.display = 'none'; state[id] = state[id] || {}; state[id].open = false; save(); }
    else { var d = DEFS[id]; makePanel(id, d.title, d.build, d.def); }
  }
  window.rencoraWidget = toggle;

  function mount() {
    var dock = document.createElement('div'); dock.className = 'rw-dock';
    Object.keys(DEFS).forEach(function (id) {
      var b = document.createElement('button'); b.textContent = DEFS[id].title;
      b.onclick = function () { toggle(id); }; dock.appendChild(b);
    });
    document.body.appendChild(dock);
    // reopen widgets that were open last time
    Object.keys(DEFS).forEach(function (id) { if (state[id] && state[id].open) { var d = DEFS[id]; makePanel(id, d.title, d.build, d.def); } });
  }
  if (document.readyState !== 'loading') mount(); else document.addEventListener('DOMContentLoaded', mount);
})();
