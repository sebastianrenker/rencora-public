/* Rencora shared boot intro — kurzer HUD-Hochfahr-Effekt für Flächen ohne eigenes Boot.
   Nutzt die aktive Identität (Name + Akzentfarbe via window.IDENT / --cy). Überspringbar per
   Klick/Taste, im Sparmodus (rencora_lite / ?lite) fast sofort. Engine Mark-LI/FatihMakes CC BY-NC. */
(function () {
  var lite = false;
  try { lite = new URLSearchParams(location.search).has('lite') || localStorage.getItem('rencora_lite') === '1'; } catch (e) {}
  var prefersReduced = false;
  try { prefersReduced = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}
  var quick = lite || prefersReduced;

  function accent() {
    if (window.IDENT && window.IDENT.cur) return window.IDENT.cur.cy;
    try {
      var cs = getComputedStyle(document.documentElement);
      return (cs.getPropertyValue('--cy') || cs.getPropertyValue('--pp') || '#b06bff').trim() || '#b06bff';
    } catch (e) { return '#b06bff'; }
  }
  function name() { return (window.IDENT && window.IDENT.cur && window.IDENT.cur.name) || 'RENCORA'; }

  function mount() {
    if (document.getElementById('rboot')) return;
    var ac = accent();
    var css = document.createElement('style');
    css.textContent =
      '#rboot{position:fixed;inset:0;z-index:99998;background:#02060c;display:flex;align-items:center;' +
      'justify-content:center;flex-direction:column;transition:opacity .45s ease;cursor:pointer}' +
      '#rboot.hide{opacity:0}' +
      '#rboot .rw{position:relative;width:210px;height:210px;display:flex;align-items:center;justify-content:center}' +
      '#rboot .ring{position:absolute;border-radius:50%;border:2px solid ' + ac + ';opacity:.55}' +
      '#rboot .r1{inset:0;animation:rbspin 2.2s linear infinite}' +
      '#rboot .r2{inset:34px;border-style:dashed;opacity:.35;animation:rbspin 3.4s linear infinite reverse}' +
      '#rboot .core{width:64px;height:64px;border-radius:50%;background:radial-gradient(circle,#fff, ' + ac + ' 60%,transparent 72%);' +
      'box-shadow:0 0 42px ' + ac + ';animation:rbpulse 1.1s ease-in-out infinite}' +
      '#rboot .bn{margin-top:26px;font:700 clamp(26px,6vw,54px)/1 system-ui,sans-serif;letter-spacing:.34em;' +
      'color:' + ac + ';text-shadow:0 0 26px ' + ac + ';padding-left:.34em}' +
      '#rboot .st{margin-top:14px;font:600 11px/1 ui-monospace,monospace;letter-spacing:.32em;color:#5ef2a0;opacity:.85}' +
      '@keyframes rbspin{to{transform:rotate(360deg)}}' +
      '@keyframes rbpulse{0%,100%{transform:scale(.9);opacity:.85}50%{transform:scale(1.08);opacity:1}}';
    document.head.appendChild(css);

    var o = document.createElement('div');
    o.id = 'rboot';
    o.innerHTML = '<div class="rw"><div class="ring r1"></div><div class="ring r2"></div><div class="core"></div></div>' +
                  '<div class="bn">' + name() + '</div><div class="st">SYSTEM ONLINE</div>';
    document.body.appendChild(o);

    var done = false;
    function close() {
      if (done) return; done = true;
      o.classList.add('hide');
      setTimeout(function () { if (o.parentNode) o.parentNode.removeChild(o); }, 480);
    }
    o.addEventListener('click', close);
    var onKey = function () { close(); document.removeEventListener('keydown', onKey); };
    document.addEventListener('keydown', onKey);
    setTimeout(close, quick ? 350 : 1150);
  }

  if (document.body) mount();
  else document.addEventListener('DOMContentLoaded', mount);
})();
