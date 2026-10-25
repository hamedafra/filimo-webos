// webOS injects this file into every page the app opens.
//
// tv.filimo.com ships its own Persian/English on-screen keyboard for search,
// but hides it when webOS.platform.tv is set and leaves typing to the TV's
// system keyboard, which often has no Persian layout. On the search page we
// report "not a TV" to the search screen only, and make the search field
// read-only so the system keyboard stays closed.
(function () {
  'use strict';

  function onSearchPage() {
    return /\/search\/?$/.test(window.location.pathname);
  }

  // The main bundle (API "os" header, Back key, analytics) keeps seeing the
  // real value; only the lazily loaded screens get the override.
  function calledFromMainBundle() {
    var frames = String(new Error().stack || '').split('\n');
    for (var i = 0; i < frames.length; i++) {
      var m = /https?:\/\/tv\.filimo\.com\/([^\s:)?]+\.js)/.exec(frames[i]);
      if (!m || /^(vendor|runtime)/.test(m[1])) continue;
      return /^index\./.test(m[1]);
    }
    return true;
  }

  function patchPlatform(webOS) {
    var platform = webOS && webOS.platform;
    if (!platform || platform.__faKeyboard) return;
    var realTv = platform.tv;
    Object.defineProperty(platform, 'tv', {
      configurable: true,
      enumerable: true,
      get: function () {
        return realTv && !(onSearchPage() && !calledFromMainBundle());
      }
    });
    Object.defineProperty(platform, '__faKeyboard', { value: true });
  }

  // The site's bundle assigns window.webOS itself; catch that assignment.
  var current = window.webOS;
  patchPlatform(current);
  try {
    Object.defineProperty(window, 'webOS', {
      configurable: true,
      enumerable: true,
      get: function () { return current; },
      set: function (value) {
        current = value;
        patchPlatform(value);
      }
    });
  } catch (e) {}

  function lockSearchInput() {
    var input = document.getElementById('searchInput');
    if (input && !input.readOnly) input.readOnly = true;
  }

  new MutationObserver(lockSearchInput).observe(document.documentElement, {
    childList: true,
    subtree: true
  });
})();
