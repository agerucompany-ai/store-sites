/* 天ぷら大塩サイト: 広告から来た印（gclid 等）を予約ボタンへ引き継ぎ、予約ボタンが押されたことを GA4 に記録する。
   2026-11-16 オーナー指示「広告→店ページ→予約ボタン→予約ページの動線と、どこで落ちたかを測る」。
   予約ページ（yoyaku.tempuraoshio.com）は URL の gclid/utm を受け取って予約に記録する。個人情報は扱わない。 */
(function () {
  var KEYS = ['gclid', 'gbraid', 'wbraid', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'];
  var RSV = /^https:\/\/(yoyaku\.tempuraoshio\.com|yoyaku\.toreta\.in|www\.hotpepper\.jp)\//;
  var keep = {};
  try { keep = JSON.parse(sessionStorage.getItem('oshio_attr') || '{}') || {}; } catch (e) { keep = {}; }
  try {
    var q = new URLSearchParams(location.search), got = false;
    KEYS.forEach(function (k) { var v = q.get(k); if (v) { keep[k] = v.slice(0, 200); got = true; } });
    if (got) sessionStorage.setItem('oshio_attr', JSON.stringify(keep));
  } catch (e) {}
  function decorate() {
    var links = document.querySelectorAll('a[href]');
    for (var i = 0; i < links.length; i++) {
      var a = links[i], h = a.getAttribute('href') || '';
      if (!RSV.test(h)) continue;
      try {
        var u = new URL(h);
        Object.keys(keep).forEach(function (k) { if (!u.searchParams.has(k)) u.searchParams.set(k, keep[k]); });
        a.href = u.toString();
        if (!a.getAttribute('data-trk')) {
          a.setAttribute('data-trk', '1');
          a.addEventListener('click', (function (dest) {
            return function () {
              if (typeof window.gtag === 'function') {
                window.gtag('event', 'reserve_click', { link_url: dest, page_path: location.pathname, from_ad: keep.gclid || keep.gbraid || keep.wbraid ? 'yes' : 'no', transport_type: 'beacon' });
              }
            };
          })(u.origin + u.pathname));
        }
      } catch (e) {}
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', decorate); else decorate();
})();
