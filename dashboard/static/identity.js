/* Rencora ↔ Jarvis identity — shared name + accent switcher for all surfaces.
   Rencora = lila (#b06bff), Jarvis = cyan (#38e6ff). Nur Name + Farbe ändern sich.
   Zustand in localStorage 'rencora_identity' (geteilt über alle Seiten).
   Engine Mark-LI/FatihMakes CC BY-NC. */
(function () {
  var IDENT = {
    rencora: { name: 'RENCORA', cy: '#b06bff', cy2: '#7a3fe0', dim: '#6a4fa0', core: '#f0e6ff', rgb: [176, 107, 255] },
    jarvis:  { name: 'JARVIS',  cy: '#38e6ff', cy2: '#0a9dff', dim: '#0b5f8f', core: '#eafcff', rgb: [56, 230, 255] }
  };
  var key = localStorage.getItem('rencora_identity') || 'rencora';
  if (!IDENT[key]) key = 'rencora';

  function apply(k) {
    if (IDENT[k]) key = k;
    try { localStorage.setItem('rencora_identity', key); } catch (e) {}
    var c = IDENT[key], r = document.documentElement.style;
    // set every accent alias a single-accent page might use, so the palette follows the identity
    r.setProperty('--cy', c.cy);  r.setProperty('--cy2', c.cy2);
    r.setProperty('--pp', c.cy);  r.setProperty('--pp2', c.cy2);
    r.setProperty('--dim', c.dim); r.setProperty('--core', c.core);
    r.setProperty('--accent', c.cy); r.setProperty('--accent2', c.cy2);
    r.setProperty('--accent-rgb', c.rgb.join(','));
    document.documentElement.setAttribute('data-look', key);
    var names = document.querySelectorAll('.ident-name,#brandName,#idlabel,#bootBrand');
    for (var i = 0; i < names.length; i++) names[i].textContent = c.name;
    if (window.ORB) { window.ORB.rgb = c.rgb; window.ORB.core = c.core; }
    if (/^(RENCORA|JARVIS)/.test(document.title)) document.title = document.title.replace(/^(RENCORA|JARVIS)/, c.name);
    try { window.dispatchEvent(new CustomEvent('identitychange', { detail: { key: key, ident: c } })); } catch (e) {}
  }
  function toggle() { apply(key === 'rencora' ? 'jarvis' : 'rencora'); }

  window.IDENT = { data: IDENT, apply: apply, toggle: toggle,
                   get key() { return key; }, get cur() { return IDENT[key]; } };

  function mountBtn() {
    var b = document.getElementById('idbtn');
    if (b) { b.addEventListener('click', toggle); return; }   // page already has its own button
    b = document.createElement('button');
    b.id = 'idbtn'; b.type = 'button'; b.textContent = '⇄';
    b.title = 'Rencora ⇄ Jarvis'; b.setAttribute('aria-label', 'Rencora/Jarvis umschalten');
    b.style.cssText = 'position:fixed;right:12px;top:12px;z-index:9999;width:34px;height:34px;' +
      'border-radius:9px;border:1px solid var(--cy,#b06bff);background:rgba(2,4,10,.5);' +
      'color:var(--cy,#b06bff);font:600 15px system-ui,sans-serif;cursor:pointer;line-height:1;' +
      '-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px)';
    b.addEventListener('click', toggle);
    document.body.appendChild(b);
  }

  function onReady() { apply(key); mountBtn(); }   // re-apply so name-holders (parsed after <head>) sync
  apply(key);   // apply colours ASAP on <html> (before inline page scripts read window.IDENT)
  if (document.readyState !== 'loading') onReady();
  else document.addEventListener('DOMContentLoaded', onReady);
})();
