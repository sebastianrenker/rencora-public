/* Rencora Radial-Menü — HoloMat-Stil: ein zentraler Core-Button, um den die Flächen-Icons in
   einem Halbkreis auffächern (wie ConceptBytes' HoloMat-Kreismenü). Zum schnellen Springen
   zwischen den Oberflächen. Identitätsfarben. Engine Mark-LI/FatihMakes CC BY-NC. */
(function () {
  var APPS = [
    { icon: '🖐️', label: 'TISCH', href: '/desk' },
    { icon: '🌐', label: 'WALL', href: '/wall' },
    { icon: '🧊', label: '3D', href: '/holo3d' },
    { icon: '🧠', label: 'BRAIN', href: '/brain' },
    { icon: '📡', label: 'FIRE TV', href: '/tv' },
    { icon: '📱', label: 'REMOTE', href: '/remote' },
    { icon: '⚙️', label: 'SETUP', href: '/settings' }
  ];
  var css = document.createElement('style');
  css.textContent =
    '#rad-core{position:fixed;left:50%;bottom:66px;transform:translateX(-50%);z-index:9200;width:56px;height:56px;' +
    'border-radius:50%;border:2px solid var(--cy,#b06bff);background:radial-gradient(circle,rgba(120,90,220,.5),rgba(2,4,10,.7));' +
    'color:var(--cy,#b06bff);font-size:22px;cursor:pointer;box-shadow:0 0 22px var(--cy,#b06bff);' +
    'display:flex;align-items:center;justify-content:center;transition:transform .25s}' +
    '#rad-core.open{transform:translateX(-50%) rotate(135deg)}' +
    '.rad-item{position:fixed;z-index:9190;width:52px;height:52px;border-radius:50%;' +
    'border:1px solid var(--cy,#b06bff);background:rgba(4,10,20,.82);display:flex;flex-direction:column;' +
    'align-items:center;justify-content:center;cursor:pointer;text-decoration:none;opacity:0;' +
    'transition:left .3s cubic-bezier(.2,.8,.3,1.3),bottom .3s cubic-bezier(.2,.8,.3,1.3),opacity .25s;' +
    '-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px);box-shadow:0 0 16px rgba(0,0,0,.5)}' +
    '.rad-item .ic{font-size:20px;line-height:1}.rad-item .lb{font:600 7px system-ui;letter-spacing:1px;color:var(--cy,#b06bff);margin-top:2px}' +
    '.rad-item:hover{background:var(--cy,#b06bff)}.rad-item:hover .lb{color:#02121f}';
  (document.head || document.documentElement).appendChild(css);

  var open = false, items = [];
  function core() { return document.getElementById('rad-core'); }
  function layout() {
    var cx = innerWidth / 2, cy = innerHeight - 66 - 28, R = Math.min(230, innerWidth * 0.32);
    var n = items.length;
    items.forEach(function (el, i) {
      // fan across an upper half-circle (180°..360°)
      var a = Math.PI + (i + 0.5) / n * Math.PI;
      var x = cx + Math.cos(a) * R, y = cy + Math.sin(a) * R;
      if (open) { el.style.left = (x - 26) + 'px'; el.style.bottom = (innerHeight - y - 26) + 'px'; el.style.opacity = '1'; el.style.pointerEvents = 'auto'; }
      else { el.style.left = (cx - 26) + 'px'; el.style.bottom = '66px'; el.style.opacity = '0'; el.style.pointerEvents = 'none'; }
    });
  }
  function toggle() { open = !open; core().classList.toggle('open', open); layout(); }

  function mount() {
    var c = document.createElement('button'); c.id = 'rad-core'; c.type = 'button'; c.textContent = '✦';
    c.title = 'Menü'; c.setAttribute('aria-label', 'Radial-Menü'); c.addEventListener('click', toggle);
    document.body.appendChild(c);
    APPS.forEach(function (a) {
      var el = document.createElement('a'); el.className = 'rad-item'; el.href = a.href;
      el.innerHTML = '<span class="ic">' + a.icon + '</span><span class="lb">' + a.label + '</span>';
      el.style.left = (innerWidth / 2 - 26) + 'px'; el.style.bottom = '66px';
      document.body.appendChild(el); items.push(el);
    });
    layout();
    addEventListener('resize', function () { if (open) layout(); });
  }
  if (document.readyState !== 'loading') mount(); else document.addEventListener('DOMContentLoaded', mount);
})();
