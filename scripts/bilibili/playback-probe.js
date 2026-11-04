/* Bilibili playback API probe. Observes URL path only; never changes traffic. */
(function () {
  try {
    const url = String(($request && $request.url) || "");
    const path = url.split("?")[0];
    const code = $response && $response.status;
    console.log("[BiliProbe] response=" + code + " " + path);
  } catch (e) {
    console.log("[BiliProbe] diagnostic error: " + String(e));
  }
  $done({});
})();
