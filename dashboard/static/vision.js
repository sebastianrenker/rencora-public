/* Rencora Vision client — schiebt regelmäßig den aktuellen Webcam-Frame zum Server (damit die
   Sprach-Funktion 'was siehst du' ein aktuelles Bild hat) und bietet einen 👁-Knopf, der Gemini
   fragt, was die Kamera sieht. Auf Kamera-Seiten einbinden (Tisch, 3D, Panel).
   Endpunkte sind _local-gated (localhost/Tailscale). Engine Mark-LI/FatihMakes CC BY-NC. */
(function () {
  function video() {
    var v = document.getElementById('cam');
    if (v && v.videoWidth) return v;
    var vs = document.getElementsByTagName('video');
    for (var i = 0; i < vs.length; i++) { if (vs[i].videoWidth) return vs[i]; }
    return null;
  }
  function grab(maxW) {
    var v = video(); if (!v || !v.videoWidth) return '';
    maxW = maxW || 640;
    var s = Math.min(1, maxW / v.videoWidth);
    var c = document.createElement('canvas');
    c.width = Math.round(v.videoWidth * s); c.height = Math.round(v.videoHeight * s);
    try { c.getContext('2d').drawImage(v, 0, 0, c.width, c.height); return c.toDataURL('image/jpeg', 0.7); }
    catch (e) { return ''; }
  }
  function post(url, payload) {
    return fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(function (r) { return r.json(); }).catch(function () { return null; });
  }
  // regelmäßiger Frame-Push (best effort) für das 'look'-Plugin
  setInterval(function () { var img = grab(480); if (img) post('/api/vision-frame', { image: img }); }, 4000);

  function toast(txt) {
    var t = document.getElementById('rvtoast');
    if (!t) {
      t = document.createElement('div'); t.id = 'rvtoast';
      t.style.cssText = 'position:fixed;left:50%;bottom:70px;transform:translateX(-50%);z-index:9998;' +
        'max-width:min(560px,86vw);background:rgba(2,6,14,.92);color:var(--cy,#b06bff);' +
        'border:1px solid var(--cy,#b06bff);border-radius:10px;padding:12px 16px;font:14px/1.5 system-ui,sans-serif;' +
        'box-shadow:0 0 24px rgba(0,0,0,.5);-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px)';
      document.body.appendChild(t);
    }
    t.textContent = txt; t.style.opacity = '1';
  }
  window.rencoraScan = function (question) {
    toast('👁 Ich schaue…');
    var img = grab(720);
    if (!img) { toast('Keine Kamera aktiv — bitte Kamerazugriff erlauben.'); return Promise.resolve(''); }
    return post('/api/vision', { image: img, question: question || '' }).then(function (r) {
      var txt = (r && r.text) || (r && r.error) || 'Kein Kamerabild verfügbar.';
      toast(txt);
      try { window.dispatchEvent(new CustomEvent('visionresult', { detail: { text: txt } })); } catch (e) {}
      return txt;
    });
  };
  function mount() {
    var ex = document.getElementById('scanbtn');
    if (ex) { ex.addEventListener('click', function () { window.rencoraScan(); }); return; }
    var b = document.createElement('button'); b.id = 'scanbtn'; b.type = 'button'; b.textContent = '👁 WAS SIEHST DU';
    b.title = 'Kamera beschreiben lassen';
    b.style.cssText = 'position:fixed;right:12px;top:56px;z-index:9999;padding:8px 12px;border-radius:9px;' +
      'border:1px solid var(--cy,#b06bff);background:rgba(2,4,10,.5);color:var(--cy,#b06bff);' +
      'font:600 12px system-ui,sans-serif;letter-spacing:1px;cursor:pointer;' +
      '-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px)';
    b.addEventListener('click', function () { window.rencoraScan(); });
    document.body.appendChild(b);
  }
  if (document.readyState !== 'loading') mount(); else document.addEventListener('DOMContentLoaded', mount);
})();
