/* Rencora Objekt-Labor — KOSTENLOSE Objekterkennung im Browser (TensorFlow.js: MobileNet für
   breite Klassifikation über 1000 Klassen + COCO-SSD für Boxen) und Analyse (Was ist das /
   Analysieren / Zerlegen / Bauen). Die Analyse spricht Rencora in IHRER Stimme (über den
   Assistenten, wenn ein Token da ist) — sonst Browser-Stimme. Kein Token/Abrechnung für die
   Erkennung. Auf Kamera-Seiten einbinden. Engine Mark-LI/FatihMakes CC BY-NC. */
(function () {
  var TF = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js';
  var COCO = 'https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd@2.2.3/dist/coco-ssd.min.js';
  var MOBI = 'https://cdn.jsdelivr.net/npm/@tensorflow-models/mobilenet@2.1.1/dist/mobilenet.min.js';
  var full = false;
  var vid = null, overlay = null, cocoModel = null, mobiModel = null;
  var boxLabels = [], clsLabels = [], lastPush = 0, lastCls = 0, ws = null;
  var TOKEN = (function () { try { return sessionStorage.getItem('jarvis_token') || ''; } catch (e) { return ''; } })();

  var DE = { person: 'Person', bottle: 'Flasche', cup: 'Tasse', 'cell phone': 'Handy', laptop: 'Laptop',
    keyboard: 'Tastatur', mouse: 'Maus', remote: 'Fernbedienung', book: 'Buch', scissors: 'Schere',
    clock: 'Uhr', tv: 'Bildschirm', chair: 'Stuhl', 'potted plant': 'Pflanze', knife: 'Messer',
    spoon: 'Löffel', fork: 'Gabel', bowl: 'Schüssel', 'wine glass': 'Glas', banana: 'Banane',
    apple: 'Apfel', orange: 'Orange', 'teddy bear': 'Teddy', backpack: 'Rucksack', umbrella: 'Schirm',
    handbag: 'Tasche', toothbrush: 'Zahnbürste', 'hair drier': 'Föhn', vase: 'Vase', wallet: 'Geldbörse' };
  function de(l) { return DE[l] || l; }
  function allLabels() {
    var seen = {}, out = [];
    boxLabels.concat(clsLabels).forEach(function (l) { var k = l.toLowerCase(); if (l && !seen[k]) { seen[k] = 1; out.push(l); } });
    return out;
  }

  function ensureVideo(cb) {
    var v = document.getElementById('cam');
    if (v && v.srcObject) { vid = v; cb(); return; }
    v = document.getElementById('objlab-cam');
    if (!v) {
      v = document.createElement('video'); v.id = 'objlab-cam'; v.autoplay = true; v.playsInline = true; v.muted = true;
      if (full) v.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;';
      else v.style.cssText = 'position:fixed;right:14px;bottom:66px;width:240px;border:1px solid var(--cy,#b06bff);border-radius:8px;z-index:30;';
      document.body.appendChild(v);
    }
    var tryCam = function (constraints, onerr) {
      navigator.mediaDevices.getUserMedia(constraints)
        .then(function (s) { v.srcObject = s; vid = v; v.onloadedmetadata = function () { v.play(); cb(); }; })
        .catch(onerr);
    };
    tryCam({ video: { facingMode: { ideal: 'environment' }, width: 1280, height: 720 } },
      function () { tryCam({ video: true }, function () { status('⚠️ Keine Kamera / kein Zugriff'); }); });
  }

  function mkOverlay() { overlay = document.createElement('canvas'); overlay.id = 'objlab-ov';
    overlay.style.cssText = 'position:fixed;z-index:31;pointer-events:none;'; document.body.appendChild(overlay); }
  function fitOverlay() {
    if (!vid || !overlay) return;
    var r = vid.getBoundingClientRect();
    overlay.style.left = r.left + 'px'; overlay.style.top = r.top + 'px';
    overlay.width = r.width; overlay.height = r.height; overlay.style.width = r.width + 'px'; overlay.style.height = r.height + 'px';
  }

  var resultBox;
  function mkUI() {
    var bar = document.createElement('div');
    bar.style.cssText = 'position:fixed;left:50%;bottom:14px;transform:translateX(-50%);z-index:40;display:flex;' +
      'flex-wrap:wrap;gap:8px;align-items:center;max-width:94vw;background:rgba(4,10,20,.85);' +
      'border:1px solid var(--cy,#b06bff);border-radius:14px;padding:10px 14px;-webkit-backdrop-filter:blur(5px);' +
      'backdrop-filter:blur(5px);font:13px system-ui,sans-serif;color:var(--ink,#e7ecff);';
    bar.innerHTML = '<span id="objlab-lbl" style="min-width:140px;color:var(--cy,#b06bff)">🔍 lädt Erkennung…</span>';
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
  function status(t) { var e = document.getElementById('objlab-lbl'); if (e) e.textContent = t; }
  function showResult(title, text) {
    resultBox.style.display = 'block';
    resultBox.innerHTML = '<span style="float:right;cursor:pointer;color:var(--dim,#8fa3c0)" id="objlab-x">✕</span>' +
      '<b style="color:var(--cy,#b06bff)">🔍 ' + title + '</b><br><br><span id="objlab-res"></span>';
    document.getElementById('objlab-res').textContent = text || '';
    document.getElementById('objlab-x').onclick = function () { resultBox.style.display = 'none'; try { speechSynthesis.cancel(); } catch (e) {} };
  }

  function analyze(mode) {
    var phrase = { identify: 'Was ist das Objekt vor der Kamera?', analysieren: 'Analysiere das erkannte Objekt genau.',
      zerlegen: 'Wie zerlege ich das erkannte Objekt?', bauen: 'Wie baue ich das erkannte Objekt zusammen?' }[mode] || 'Was ist das?';
    if (TOKEN) {   // JARVIS-Stimme: Groq analysiert (kostenlos), Rencora spricht es in ihrer Stimme
      showResult(mode, 'Rencora analysiert…');
      fetch('/api/lab-speak', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOKEN },
        body: JSON.stringify({ labels: allLabels(), mode: mode }) })
        .then(function (r) { return r.json(); }).then(function (d) {
          var el = document.getElementById('objlab-res'); if (el) el.textContent = (d && d.text) || 'Konnte gerade nicht analysieren.';
        }).catch(function () { var el = document.getElementById('objlab-res'); if (el) el.textContent = 'Analyse fehlgeschlagen.'; });
      return;
    }
    // Fallback ohne Assistent: Text holen + Browser-Stimme
    showResult(mode, 'Analysiere…');
    fetch('/api/lab-analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ labels: allLabels(), mode: mode }) })
      .then(function (r) { return r.json(); }).then(function (d) {
        var t = (d && d.text) || 'Konnte gerade nicht analysieren.';
        document.getElementById('objlab-res').textContent = t;
        try { if (window.speechSynthesis) { var u = new SpeechSynthesisUtterance(t); u.lang = 'de-DE'; speechSynthesis.cancel(); speechSynthesis.speak(u); } } catch (e) {}
      }).catch(function () { document.getElementById('objlab-res').textContent = 'Analyse fehlgeschlagen.'; });
  }

  function connectWS() {
    if (!TOKEN) return;
    try {
      var proto = location.protocol === 'https:' ? 'wss' : 'ws';
      ws = new WebSocket(proto + '://' + location.host + '/ws?token=' + encodeURIComponent(TOKEN));
      ws.onmessage = function (e) { var m; try { m = JSON.parse(e.data); } catch (x) { return; }
        if (m.type === 'log' && m.speaker === 'jarvis' && resultBox && resultBox.style.display === 'block') {
          var r = document.getElementById('objlab-res'); if (r) r.textContent = m.text;
        }
      };
    } catch (x) {}
  }

  function loop() {
    if (!cocoModel || !vid || vid.readyState < 2) { requestAnimationFrame(loop); return; }
    fitOverlay();
    cocoModel.detect(vid).then(function (preds) {
      var ctx = overlay.getContext('2d'); ctx.clearRect(0, 0, overlay.width, overlay.height);
      var sx = overlay.width / (vid.videoWidth || 1), sy = overlay.height / (vid.videoHeight || 1);
      var ac = (getComputedStyle(document.documentElement).getPropertyValue('--cy') || '#b06bff').trim();
      var found = [];
      preds.forEach(function (p) {
        if (p.score < 0.4) return;
        var x = p.bbox[0] * sx, y = p.bbox[1] * sy, w = p.bbox[2] * sx, h = p.bbox[3] * sy;
        ctx.strokeStyle = ac; ctx.lineWidth = 2; ctx.strokeRect(x, y, w, h);
        var lbl = de(p.class);
        ctx.fillStyle = 'rgba(2,6,14,0.8)'; ctx.font = '600 13px system-ui';
        var tw = ctx.measureText(lbl).width + 10; ctx.fillRect(x, y - 18, tw, 18);
        ctx.fillStyle = '#fff'; ctx.fillText(lbl, x + 5, y - 5);
        found.push(lbl);
      });
      boxLabels = found;
      // MobileNet: breite Klassifikation (1000 Klassen), Top-3, ~alle 1.2 s
      var now = Date.now();
      if (mobiModel && now - lastCls > 1200) {
        lastCls = now;
        mobiModel.classify(vid, 3).then(function (res) {
          clsLabels = (res || []).filter(function (r) { return r.probability > 0.12; })
            .map(function (r) { return de(r.className.split(',')[0].trim()); });
          refresh();
        }).catch(function () {});
      }
      refresh();
      requestAnimationFrame(loop);
    }).catch(function () { requestAnimationFrame(loop); });
  }
  function refresh() {
    var all = allLabels();
    status(all.length ? ('🔍 ' + all.slice(0, 5).join(', ')) : '🔍 nichts erkannt — näher/heller halten');
    var now = Date.now();
    if (now - lastPush > 2500) { lastPush = now;
      fetch('/api/lab-detect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ labels: all }) }).catch(function () {}); }
  }

  function loadScript(src) { return new Promise(function (res, rej) { var s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = rej; document.head.appendChild(s); }); }
  function boot() {
    full = document.body.getAttribute('data-objlab') === 'full';
    mkOverlay(); mkUI(); connectWS();
    ensureVideo(function () {
      addEventListener('resize', fitOverlay);
      loadScript(TF).then(function () { return loadScript(MOBI).catch(function () {}); })
        .then(function () { return loadScript(COCO); })
        .then(function () { return cocoSsd.load(); })
        .then(function (m) {
          cocoModel = m; status('🔍 bereit — halte etwas vor die Kamera');
          if (window.mobilenet) mobilenet.load().then(function (mm) { mobiModel = mm; }).catch(function () {});
          requestAnimationFrame(loop);
        }).catch(function () { status('⚠️ Erkennung konnte nicht laden (Internet?)'); });
    });
  }
  if (document.readyState !== 'loading') boot(); else document.addEventListener('DOMContentLoaded', boot);
})();
