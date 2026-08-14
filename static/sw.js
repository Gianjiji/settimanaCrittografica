// v2 drops every page cached while one log was shared: those copies carry someone
// else's ticks, and the activate handler below deletes any cache but the current one.
var CACHE = "settimana-crittografica-v2";
var CORE = ["/", "/static/style.css", "/static/app.js"];

self.addEventListener("install", function (event) {
  event.waitUntil(caches.open(CACHE).then(function (cache) { return cache.addAll(CORE); }));
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (key) { return key !== CACHE; })
      .map(function (key) { return caches.delete(key); }));
  }));
  self.clients.claim();
});

// Network first, so a fresh fascicle always wins, with the cached copy as fallback.
self.addEventListener("fetch", function (event) {
  if (event.request.method !== "GET") { return; }
  event.respondWith(
    fetch(event.request).then(function (response) {
      var copy = response.clone();
      caches.open(CACHE).then(function (cache) { cache.put(event.request, copy); });
      return response;
    }).catch(function () {
      return caches.match(event.request);
    })
  );
});
