/* Rencora Objekt-Labor — KOSTENLOSE Objekterkennung im Browser (TensorFlow.js: COCO-SSD +
   MobileNet), Live-Boxen über der Kamera, plus Analyse (Was ist das / Analysieren / Zerlegen /
   Bauen) über Grok/Groq. Kein Token, keine Abrechnung. Auf Kamera-Seiten (Objekt-Labor, Tisch,
   Leinwand) einbinden. Engine Mark-LI/FatihMakes CC BY-NC. */
(function () {
  var TF = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js';
  var COCO = 'https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd@2.2.3/dist/coco-ssd.min.js';
  var MOBI = 'https://cdn.jsdelivr.net/npm/@tensorflow-models/mobilenet@2.1.1/dist/mobilenet.min.js';
  var full = false;   // in boot() gesetzt (document.body existiert erst dann)
  var vid = null, overlay = null, cocoModel = null, mobiModel = null, labels = [], lastPush = 0;

  // COCO-Klassen ins Deutsche (die häufigsten)
  var DE = { person: 'Person', bottle: 'Flasche', cup: 'Tasse', 'cell phone': 'Handy', laptop: 'Laptop',
    keyboard: 'Tastatur', mouse: 'Maus', remote: 'Fernbedienung', book: 'Buch', scissors: 'Schere',
    clock: 'Uhr', 'tv': 'Bildschirm', chair: 'Stuhl', 'potted plant': 'Pflanze', knife: 'Messer',
    spoon: 'Löffel', fork: 'Gabel', bowl: 'Schüssel', 'wine glass': 'Glas', banana: 'Banane',
    apple: 'Apfel', orange: 'Orange', 'teddy bear': 'Teddy', backpack: 'Rucksack', umbrella: 'Schirm',
    handbag: 'Tasche', 'toothbrush': 'Zahnbürste', 'hair drier': 'Föhn', vase: 'Vase' };
  function de(l) { return DE[l] || l; }

  function ensureVideo(cb) {
    var v = document.getElementById('cam');
    if (v && v.srcObject) { vid = v; cb(); return; }
    v = document.getElementById('objlab-cam');
    if (!v) {
      v = document.createElement('video'); v.id = 'objlab-cam'; v.autoplay = true; v.playsInline = true; v.muted = true;
      if (full) v.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;';
      else v.style.cssText = 'position:fixed;right:14px;bottom:60px;width:220px;border:1px solid var(--cy,#b06bff);border-radius:8px;z-index:30;';
      document.body.appendChild(v);
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: 1280, height: 720 } })
      .then(function (s) { v.srcObject = s; vid = v; v.onloadedmetadata = function () { v.play(); cb(); }; })
      .catch(function () {
        navigator.mediaDevices.getUserMedia({ video: true })
          .then(function (s) { v.srcObject = s; vid = v; v.onloadedmetadata = function () { v.play(); cb(); }; })
          .catch(function () { toast('Keine Kamera verfügbar.'); });
      });
  }

  function mkOverlay() {
    overlay = document.createElement('canvas');
    overlay.id = 'objlab-ov'; overlay.style.cssText = 'position:fixed;z-index:31;pointer-events:none;';
    document.body.appendChild(overlay);
  }
  function fitOverlay() {
    if (!vid || !overlay) return;
    var r = vid.getBoundingClientRect();
    overlay.style.left = r.left + 'px'; overlay.style.top = r.top + 'px';
    overlay.width = r.width; overlay.height = r.height;
    overlay.style.width = r.width + 'px'; overlay.style.height = r.height + 'px';
  }

  var bar, resultBox;
  function mkUI() {
    bar = document.createElement('div');
    bar.style.cssText = 'position:fixed;left:50%;bottom:14px;transform:translateX(-50%);z-index:40;display:flex;' +
      'flex-wrap:wrap;gap:8px;align-items:center;max-width:94vw;background:rgba(4,10,20,.85);' +
      'border:1px solid var(--cy,#b06bff);border-radius:14px;padding:10px 14px;' +
      '-webkit-backdrop-filter:blur(5px);backdrop-filter:blur(5px);font:13px system-ui,sans-serif;color:var(--ink,#e7ecff);';
    bar.innerHTML = '<span id="objlab-lbl" style="min-width:120px;color:var(--cy,#b06bff)">🔍 suche…</span>';
    [['Was ist das', 'identify'], ['Analysieren', 'analysieren'], ['Zerlegen', 'zerlegen'], ['Bauen', 'bauen']]
      .forEach(function (m) {
        var b = document.createElement('button'); b.textContent = m[0];
        b.style.cssText = 'background:rgba(120,120,255,.14);border:1px solid var(--cy,#b06bff);color:#fff;' +
          'border-radius:9px;padding:7px 11px;font:600 12px system-ui;cursor:pointer;';
        b.onclick = function () { analyze(m[1]); };
        bar.appendChild(b);
      });
    document.body.appendChild(bar);
    resultBox = document.createElement('div');
    resultBox.style.cssText = 'position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:41;display:none;' +
      'max-width:min(620px,90vw);max-height:70vh;overflow:auto;background:rgba(4,10,20,.96);' +
      'border:1px solid var(--cy,#b06bff);border-radius:14px;padding:20px 22px;color:var(--ink,#e7ecff);' +
      'font:15px/1.6 system-ui;box-shadow:0 0 40px rgba(0,0,0,.6);';
    document.body.appendChild(resultBox);
  }
  function toast(t) { var e = document.getElementById('objlab-lbl'); if (e) e.textContent = t; }

  function analyze(mode) {
    resultBox.style.display = 'block';
    resultBox.innerHTML = '<span style="float:right;cursor:pointer;color:var(--dim,#8fa3c0)" id="objlab-x">✕</span>' +
      '<b style="color:var(--cy,#b06bff)">🔍 ' + mode + '</b><br><br><span id="objlab-res">Rencora analysiert…</span>';
    document.getElementById('objlab-x').onclick = function () { resultBox.style.display = 'none'; try { speechSynthesis.cancel(); } catch (e) {} };
    fetch('/api/lab-analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ labels: labels, mode: mode }) })
      .then(function (r) { return r.json(); }).then(function (d) {
        var t = (d && d.text) || 'Konnte gerade nicht analysieren.';
        document.getElementById('objlab-res').textContent = t;
        try { if (window.speechSynthesis) { var u = new SpeechSynthesisUtterance(t); u.lang = 'de-DE'; speechSynthesis.cancel(); speechSynthesis.speak(u); } } catch (e) {}
      }).catch(function () { document.getElementById('objlab-res').textContent = 'Analyse fehlgeschlagen.'; });
  }

  function loop() {
    if (!cocoModel || !vid || vid.readyState < 2) { requestAnimationFrame(loop); return; }
    fitOverlay();
    cocoModel.detect(vid).then(function (preds) {
      var ctx = overlay.getContext('2d'); ctx.clearRect(0, 0, overlay.width, overlay.height);
      var sx = overlay.width / (vid.videoWidth || 1), sy = overlay.height / (vid.videoHeight || 1);
      var found = [];
      var ac = (getComputedStyle(document.documentElement).getPropertyValue('--cy') || '#b06bff').trim();
      preds.forEach(function (p) {
        if (p.score < 0.55) return;
        var x = p.bbox[0] * sx, y = p.bbox[1] * sy, w = p.bbox[2] * sx, h = p.bbox[3] * sy;
        ctx.strokeStyle = ac; ctx.lineWidth = 2; ctx.strokeRect(x, y, w, h);
        var lbl = de(p.class);
        ctx.fillStyle = 'rgba(2,6,14,0.8)'; ctx.font = '600 13px system-ui';
        var tw = ctx.measureText(lbl).width + 10;
        ctx.fillRect(x, y - 18, tw, 18); ctx.fillStyle = '#fff'; ctx.fillText(lbl, x + 5, y - 5);
        found.push(lbl);
      });
      // MobileNet klassifiziert das Gesamtbild → Objekt-Typ (auch Technik/Bauteile)
      if (mobiModel && Math.random() < 0.15) {
        mobiModel.classify(vid).then(function (res) {
          if (res && res[0] && res[0].probability > 0.2) {
            var c = res[0].className.split(',')[0];
            if (found.indexOf(c) < 0) found.push(c);
            updateLabels(found);
          }
        }).catch(function () {});
      } else { updateLabels(found); }
      requestAnimationFrame(loop);
    }).catch(function () { requestAnimationFrame(loop); });
  }
  function updateLabels(found) {
    labels = found;
    var e = document.getElementById('objlab-lbl');
    if (e) e.textContent = found.length ? ('🔍 ' + found.slice(0, 4).join(', ')) : '🔍 nichts erkannt';
    var now = Date.now();
    if (now - lastPush > 3000) { lastPush = now;
      fetch('/api/lab-detect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ labels: labels }) }).catch(function () {}); }
  }

  function loadScript(src) { return new Promise(function (res, rej) { var s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = rej; document.head.appendChild(s); }); }
  function boot() {
    full = document.body.getAttribute('data-objlab') === 'full';
    mkOverlay(); mkUI();
    ensureVideo(function () {
      addEventListener('resize', fitOverlay);
      loadScript(TF).then(function () { return loadScript(COCO); }).then(function () { return loadScript(MOBI).catch(function () {}); })
        .then(function () { return cocoSsd.load(); }).then(function (m) { cocoModel = m; toast('🔍 bereit');
          if (window.mobilenet) mobilenet.load().then(function (mm) { mobiModel = mm; }).catch(function () {});
          requestAnimationFrame(loop);
        }).catch(function () { toast('Erkennung konnte nicht laden (Internet?).'); });
    });
  }
  if (document.readyState !== 'loading') boot(); else document.addEventListener('DOMContentLoaded', boot);
})();
