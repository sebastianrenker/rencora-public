/* Rencora Now-Playing — schlanke Leiste unten mit dem aktuell laufenden Titel + Skip/Stop.
   Pollt /api/nowplaying; blendet sich aus, wenn keine Musik läuft. Steuert über /api/music-control.
   Identitätsfarben. Engine Mark-LI/FatihMakes CC BY-NC. */
(function () {
  var css = document.createElement('style');
  css.textContent =
    '#rnp{position:fixed;left:50%;bottom:14px;transform:translateX(-50%) translateY(120%);z-index:9300;' +
    'display:flex;align-items:center;gap:12px;max-width:min(560px,92vw);padding:9px 14px;border-radius:30px;' +
    'background:rgba(4,10,20,.82);border:1px solid var(--cy,#b06bff);color:var(--ink,#e7ecff);' +
    'box-shadow:0 0 24px rgba(0,0,0,.5);font:13px system-ui,sans-serif;opacity:0;' +
    'transition:transform .4s cubic-bezier(.2,.8,.3,1.2),opacity .4s;-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}' +
    '#rnp.on{transform:translateX(-50%) translateY(0);opacity:1}' +
    '#rnp .eq{display:flex;gap:2px;align-items:flex-end;height:16px;flex:0 0 auto}' +
    '#rnp .eq i{width:3px;background:var(--cy,#b06bff);border-radius:2px;animation:rnpeq .9s ease-in-out infinite}' +
    '#rnp .eq i:nth-child(2){animation-delay:.2s}#rnp .eq i:nth-child(3){animation-delay:.4s}#rnp .eq i:nth-child(4){animation-delay:.15s}' +
    '@keyframes rnpeq{0%,100%{height:4px}50%{height:16px}}' +
    '#rnp .tt{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    '#rnp .tt b{color:#fff}#rnp .md{color:var(--dim,#8fa3c0);font-size:11px}' +
    '#rnp button{background:transparent;border:0;color:var(--cy,#b06bff);font-size:17px;cursor:pointer;padding:2px 4px;line-height:1}' +
    '#rnp button:hover{color:#fff}';
  (document.head || document.documentElement).appendChild(css);

  var bar;
  function mount() {
    bar = document.createElement('div'); bar.id = 'rnp';
    bar.innerHTML =
      '<span class="eq"><i></i><i></i><i></i><i></i></span>' +
      '<span class="tt">—</span>' +
      '<button id="rnp-skip" title="Nächster">⏭</button>' +
      '<button id="rnp-stop" title="Stopp">⏹</button>';
    document.body.appendChild(bar);
    bar.querySelector('#rnp-skip').onclick = function () { ctl('skip'); };
    bar.querySelector('#rnp-stop').onclick = function () { ctl('stop'); setTimeout(poll, 400); };
    poll(); setInterval(poll, 5000);
  }
  function ctl(action) {
    fetch('/api/music-control', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action }) }).catch(function () {});
  }
  function esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function poll() {
    fetch('/api/nowplaying').then(function (r) { return r.json(); }).then(function (d) {
      if (d && d.playing && d.title) {
        bar.querySelector('.tt').innerHTML = '<b>♪ ' + esc(d.title) + '</b>' +
          (d.mood ? ' <span class="md">· ' + esc(d.mood) + '</span>' : '');
        bar.classList.add('on');
      } else {
        bar.classList.remove('on');
      }
    }).catch(function () { bar.classList.remove('on'); });
  }
  if (document.readyState !== 'loading') mount(); else document.addEventListener('DOMContentLoaded', mount);
})();
