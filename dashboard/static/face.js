/* Rencora Gesichts-Erkennung (Mehr-Personen) — lernt mehrere Gesichter mit Namen an (🙂-Knopf,
   fragt den Namen), speichert die Descriptoren lokal und begrüßt jede erkannte Person beim eigenen
   Namen. Fremde werden nicht begrüßt; vor dem ersten Anlernen einfache Präsenz-Begrüßung.
   face-api.js (Detector + Landmark + Recognition) vom CDN; lädt es nicht, passiert nichts.
   Engine Mark-LI/FatihMakes CC BY-NC. */
(function () {
  var owner = '';
  try { fetch('/api/status').then(function (r) { return r.json(); }).then(function (d) { owner = (d && d.owner) || ''; }).catch(function () {}); } catch (e) {}
  var MODEL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/';
  var KEY = 'rencora_faces', KEY_OLD = 'rencora_face_descriptor';
  var ready = false, matcher = null;

  function video() {
    var v = document.getElementById('cam');
    if (v && v.videoWidth) return v;
    var vs = document.getElementsByTagName('video');
    for (var i = 0; i < vs.length; i++) { if (vs[i].videoWidth) return vs[i]; }
    return null;
  }
  function speak(t) {
    try { if (!window.speechSynthesis) return; var u = new SpeechSynthesisUtterance(t); u.lang = 'de-DE';
      window.speechSynthesis.cancel(); window.speechSynthesis.speak(u); } catch (e) {}
  }
  function loadFaces() {
    var faces = [];
    try { faces = JSON.parse(localStorage.getItem(KEY) || '[]') || []; } catch (e) { faces = []; }
    if (!faces.length) {                       // Migration vom früheren Einzel-Gesicht
      try { var old = localStorage.getItem(KEY_OLD); if (old) faces = [{ name: owner || 'Owner', descriptor: JSON.parse(old) }]; } catch (e) {}
    }
    return faces;
  }
  function saveFaces(faces) { try { localStorage.setItem(KEY, JSON.stringify(faces)); } catch (e) {} }

  function buildMatcher() {
    try {
      var faces = loadFaces(); if (!faces.length) return null;
      var labeled = faces.map(function (f) {
        return new faceapi.LabeledFaceDescriptors(f.name || 'Person', [new Float32Array(f.descriptor)]);
      });
      return new faceapi.FaceMatcher(labeled, 0.55);
    } catch (e) { return null; }
  }
  function enroll() {
    var v = video();
    if (!v || !ready) { speak('Die Kamera oder die Modelle sind noch nicht bereit.'); return; }
    var name = '';
    try { name = (window.prompt('Name der Person?', owner || '') || '').trim(); } catch (e) {}
    if (!name) name = owner || 'Person';
    faceapi.detectSingleFace(v, new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceDescriptor()
      .then(function (res) {
        if (!res) { speak('Ich sehe kein Gesicht. Schaut bitte gerade in die Kamera.'); return; }
        var faces = loadFaces();
        faces = faces.filter(function (f) { return (f.name || '').toLowerCase() !== name.toLowerCase(); });  // ersetzt gleichen Namen
        faces.push({ name: name, descriptor: Array.prototype.slice.call(res.descriptor) });
        saveFaces(faces); matcher = buildMatcher();
        speak('Gesicht von ' + name + ' gespeichert. Ich erkenne ' + name + ' jetzt.');
      }).catch(function () { speak('Das Anlernen ist fehlgeschlagen.'); });
  }
  window.rencoraEnrollFace = enroll;

  function mountBtn() {
    if (document.getElementById('facebtn')) return;
    var b = document.createElement('button'); b.id = 'facebtn'; b.type = 'button'; b.textContent = '🙂';
    b.title = 'Gesicht anlernen (Name eingeben)';
    b.style.cssText = 'position:fixed;right:12px;top:100px;z-index:9999;width:34px;height:34px;border-radius:9px;' +
      'border:1px solid var(--cy,#b06bff);background:rgba(2,4,10,.5);color:var(--cy,#b06bff);' +
      'font-size:17px;cursor:pointer;-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px);';
    b.addEventListener('click', enroll);
    document.body.appendChild(b);
  }

  function start() {
    if (!window.faceapi) return;
    Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(MODEL),
      faceapi.nets.faceLandmark68Net.loadFromUri(MODEL),
      faceapi.nets.faceRecognitionNet.loadFromUri(MODEL)
    ]).then(function () {
      ready = true; matcher = buildMatcher();
      var seen = false, lastGreet = 0, lastName = '';
      setInterval(function () {
        var v = video(); if (!v) return;
        var p = faceapi.detectSingleFace(v, new faceapi.TinyFaceDetectorOptions());
        if (matcher) p = p.withFaceLandmarks().withFaceDescriptor();
        p.then(function (res) {
          var now = Date.now();
          if (!res) { seen = false; return; }
          var name = owner || '';
          if (matcher && res.descriptor) {
            var m = matcher.findBestMatch(res.descriptor);
            name = (m.label && m.label !== 'unknown') ? m.label : null;   // Fremde: nicht grüßen
          }
          // erneut grüßen, wenn eine ANDERE bekannte Person auftaucht (oder nach 1 Min Pause)
          var changed = (name && name !== lastName);
          if (name !== null && (!seen || changed) && (changed || now - lastGreet > 60000)) {
            speak('Willkommen zurück' + (name ? ', ' + name : '') + '.');
            lastGreet = now; lastName = name;
          }
          seen = true;
        }).catch(function () {});
      }, 1500);
    }).catch(function () {});
  }

  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/dist/face-api.js';
  s.onload = function () {
    start();
    if (document.readyState !== 'loading') mountBtn();
    else document.addEventListener('DOMContentLoaded', mountBtn);
  };
  s.onerror = function () {};
  (document.head || document.documentElement).appendChild(s);
})();
