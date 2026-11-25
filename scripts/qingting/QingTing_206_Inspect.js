/*
 * QingTing English 2.0.6 read-only compatibility inspection.
 * No entitlement modification; never logs identifiers, credentials or response contents.
 */
(function () {
  try {
    var url = String(($request && $request.url) || '');
    var data = JSON.parse(String(($response && $response.body) || '{}'));
    var endpoint = 'other';
    if (/\/v3\/2\/report\/launch\//.test(url)) endpoint = 'launch-v3';
    else if (/\/api\/qt\/buy\/vip\/purchase2/.test(url)) endpoint = 'vip-purchase2';
    else if (/\/api\/buy\/promote\/in-duration/.test(url)) endpoint = 'promote-duration';
    var body = data.data_body;
    var result = {
      endpoint: endpoint,
      responseJson: true,
      encrypted: data.data_encrypted === 1,
      bodyType: (body === null ? 'null' : Array.isArray(body) ? 'array' : typeof body),
      resultCodePresent: Object.prototype.hasOwnProperty.call(data, 'result_code')
    };
    if (endpoint === 'vip-purchase2' && body && typeof body === 'object') {
      result.accountPresent = Boolean(body.account && typeof body.account === 'object');
      result.vipTypeFieldPresent = Boolean(body.account && Object.prototype.hasOwnProperty.call(body.account, 'vip_type'));
      result.expiryFieldPresent = Boolean(body.account && Object.prototype.hasOwnProperty.call(body.account, 'expiry'));
    }
    if (endpoint === 'promote-duration' && body && typeof body === 'object') {
      var auth = body.auth || {};
      result.privilegeFieldsPresent = ['qtvip', 'collins', 'wordroot'].filter(function (key) {
        return Object.prototype.hasOwnProperty.call(auth, key);
      });
    }
    console.log('[QT 2.0.6 read-only] ' + JSON.stringify(result));
  } catch (err) {
    console.log('[QT 2.0.6 read-only] Could not parse response JSON; response unchanged.');
  }
  $done({});
})();