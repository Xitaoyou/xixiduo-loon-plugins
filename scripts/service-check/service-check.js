/* SPDX-License-Identifier: GPL-3.0-only
 * Loon adaptation by 西西多 of chen08209/FlClash core/service_check.go
 * and core/service_rules.go. Original authors: FlClash contributors.
 * Source: https://github.com/chen08209/FlClash
 * Distributed under GPLv3; see COPYING. Modified: 2026-11-09.
 * Manual checks only. No credentials, telemetry, cache or configuration changes.
 */
(function () {
  'use strict';
  const arg = typeof $argument === 'object' && $argument ? $argument : {};
  const timeout = Math.max(3000, Math.min(15000, Number(arg.requestTimeout || 10000)));
  const route = String(arg.route || 'current').trim();
  const labels = {available:'可达/规则通过', unavailable:'不可用', restricted:'访问受限',
    'disallowed-isp':'运营商受限', blocked:'被拦截', 'unsupported-region':'地区不支持',
    'originals-only':'仅自制内容', 'coming-soon':'尚未开放', timeout:'超时', failed:'检测失败', unknown:'未能判定'};
  const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';
  let finished = false;
  function request(url, options) {
    options = options || {};
    return new Promise(resolve => {
      let settled = false;
      const start = Date.now();
      const finish = value => { if (!settled) { settled=true; clearTimeout(timer); resolve(value); } };
      const timer = setTimeout(() => finish({error:'timeout', delay:0}), timeout + 250);
      const config = Object.assign({url, timeout, insecure:false, 'auto-redirect':true}, options);
      config.headers = Object.assign({'User-Agent':UA}, options.headers || {});
      if (route !== 'current') config.node = route;
      try {
        const method = config.body === undefined ? 'get' : 'post';
        $httpClient[method](config, (error,response,body) => {
          if (error) return finish({error:/tim(e|ed)[ -]?out/i.test(String(error))?'timeout':'failed',delay:0});
          finish({code:Number(response && (response.status || response.statusCode)),
            body:typeof body==='string'?body:'', headers:response && response.headers || {}, delay:Date.now()-start});
        });
      } catch (_) { finish({error:'failed',delay:0}); }
    });
  }
  const result = (r,status,region) => ({status:r.error || status, delay:r.delay, region:region || ''});
  const status = r => r.code>=200 && r.code<300?'available':[401,403,429,451].includes(r.code)?'restricted':'unavailable';
  const contains = (r,...terms) => terms.some(t=>String(r.body || '').toLowerCase().includes(t.toLowerCase()));
  const match = (body,re) => (String(body || '').match(re)||[])[1] || '';
  const trace = r => match(r.body, /^loc=(.+)$/m).trim();
  const region = s => ({CHN:'CN',RUS:'RU',BLR:'BY',CUB:'CU',IRN:'IR',PRK:'KP',SYR:'SY',HKG:'HK',MAC:'MO'}[s] || String(s || '').toUpperCase());
  async function reachable(url) { const r=await request(url); return result(r,status(r)); }
  async function chatgpt() {
    const ios=await request('https://ios.chat.openai.com/');
    let state=ios.error || (contains(ios,'you may be connected to a disallowed isp')?'disallowed-isp':contains(ios,'sorry, you have been blocked')?'blocked':contains(ios,'request is not allowed. please try again later.')?'available':'unknown');
    const t=await request('https://chat.openai.com/cdn-cgi/trace');
    const web=await request('https://api.openai.com/compliance/cookie_requirements');
    if (!web.error && contains(web,'unsupported_country')) state='unsupported-region';
    return {status:state,region:trace(t),delay:ios.delay};
  }
  async function claude() {
    const r=await request('https://claude.ai/cdn-cgi/trace'); const loc=trace(r);
    return result(r,!loc?'unknown':['AF','BY','CN','CU','HK','IR','KP','MO','RU','SY'].includes(loc)?'unsupported-region':'available',loc);
  }
  async function gemini() {
    const r=await request('https://gemini.google.com');
    const loc=match(r.body, /,2,1,200,"([A-Z]{3})/);
    return result(r,!loc?'unknown':['CHN','RUS','BLR','CUB','IRN','PRK','SYR','HKG','MAC'].includes(loc)?'unsupported-region':'available',region(loc));
  }
  async function youtube() {
    const r=await request('https://www.youtube.com/premium?hl=en');
    const loc=match(r.body, /id=["']country-code["'][^>]*>\s*([A-Za-z]{2,3})\s*</i) || match(r.body,/"(?:GL|countryCode|country_code)"\s*:\s*"([A-Za-z]{2})"/);
    return result(r,contains(r,'premium is not available in your country','premium is not available in your region')?'unsupported-region':status(r),loc);
  }
  async function netflix() {
    let r=await request('https://api.fast.com/netflix/speedtest/v2?https=true&token=YXNkZmFzZGxmbnNkYWZoYXNkZmhrYWxm&urlCount=5');
    if (!r.error && r.code===403) return result(r,'blocked');
    try { const j=JSON.parse(r.body); if(j.targets && j.targets.length) return result(r,'available',j.targets[0].location.country); } catch(_){}
    const a=await request('https://www.netflix.com/title/81280792');if(a.error)return result(a,'failed');
    const b=await request('https://www.netflix.com/title/70143836');if(b.error)return result(b,'failed');
    if(a.code===404 && b.code===404)return result(a,'originals-only');
    if(a.code===403 || b.code===403)return result(a,'unsupported-region');
    if([200,301].includes(a.code)||[200,301].includes(b.code)) {
      r=await request('https://www.netflix.com/title/80018499',{'auto-redirect':false});
      const key=Object.keys(r.headers || {}).find(k=>k.toLowerCase()==='location');
      return result(a,'available',match(key?r.headers[key]:'',/^https?:\/\/[^/]+\/([a-zA-Z]{2})(?:-|\/)/));
    }
    return result(a,status(a));
  }
  async function prime() { const r=await request('https://www.primevideo.com');const loc=match(r.body,/"currentTerritory":"([^"]+)"/);return result(r,contains(r,'isServiceRestricted')?'unsupported-region':loc?'available':'unknown',loc); }
  async function spotify() { const r=await request('https://www.spotify.com/api/content/v1/country-selector?platform=web&format=json');return result(r,[403,451].includes(r.code)||contains(r,'not available in your country')?'unsupported-region':status(r),match(r.body,/"countryCode"\s*:\s*"([^"]+)"/)); }
  async function tiktok() { const r=await request('https://www.tiktok.com/');return result(r,[403,451].includes(r.code)||contains(r,'access denied','not available in your region','tiktok is not available')?'unsupported-region':status(r),match(r.body,/"webapp\.app-context"\s*:\s*\{[^{}]*?"region"\s*:\s*"([^"]*)"/)); }
  async function discord() { const r=await request('https://discord.com/api/v9/auth/location-metadata');return result(r,status(r),match(r.body,/"country_code"\s*:\s*"([^"]+)"/)); }
  async function bilibili() {
    const urls=['https://api.bilibili.com/pgc/player/web/playurl?avid=82846771&qn=0&type=&otype=json&ep_id=307247&fourk=1&fnver=0&fnval=16&module=bangumi','https://api.bilibili.com/pgc/player/web/playurl?avid=18281381&cid=29892777&qn=0&type=&otype=json&ep_id=183799&fourk=1&fnver=0&fnval=16&module=bangumi'];
    for(let i=0;i<urls.length;i++){const r=await request(urls[i]);const code=match(r.body,/^\s*\{\s*"code"\s*:\s*(-?\d+)/);if(r.error)return result(r,'failed');if(code==='0')return result(r,'available',i===0?'CN':'');if(code!=='-10403'||i===1)return result(r,code==='-10403'?'unsupported-region':'unknown');}
  }
  async function disney() {
    const auth='Bearer ZGlzbmV5JmJyb3dzZXImMS4wLjA.Cu56AgSfBTDag5NiRA81oLHkDZfu5L3CKadnefEAY84';
    const headers={authorization:auth,'content-type':'application/json; charset=UTF-8'};
    const a=await request('https://disney.api.edge.bamgrid.com/devices',{headers,body:JSON.stringify({deviceFamily:'browser',applicationRuntime:'chrome',deviceProfile:'windows',attributes:{}})});
    if(a.error || a.code===403)return result(a,a.code===403?'blocked':'failed');
    const assertion=match(a.body,/"assertion"\s*:\s*"([^"]+)"/);if(!assertion)return result(a,'unknown');
    const b=await request('https://disney.api.edge.bamgrid.com/token',{headers:{authorization:auth,'content-type':'application/x-www-form-urlencoded'},body:'grant_type=urn:ietf:params:oauth:grant-type:token-exchange&latitude=0&longitude=0&platform=browser&subject_token='+encodeURIComponent(assertion)+'&subject_token_type=urn:bamtech:params:oauth:token-type:device'});
    if(b.error || contains(b,'forbidden-location','403 ERROR'))return result(b,'blocked');
    const refresh=match(b.body,/"refresh_token"\s*:\s*"([^"]+)"/);if(!refresh)return result(b,'unknown');
    const c=await request('https://disney.api.edge.bamgrid.com/graph/v1/device/graphql',{headers,body:JSON.stringify({query:'mutation refreshToken($input: RefreshTokenInput!) { refreshToken(refreshToken: $input) { activeSession { sessionId } } }',variables:{input:{refreshToken:refresh}}})});
    if(c.error || c.code>=400)return result(c,'failed');
    const loc=match(c.body,/"countryCode"\s*:\s*"([^"]+)"/);const supported=match(c.body,/"inSupportedLocation"\s*:\s*(false|true)/);
    return result(a,!loc?'unknown':supported==='true'?'available':supported==='false'?'coming-soon':'unknown',loc);
  }
  const checks=[['google','Google',()=>reachable('https://www.google.com/generate_204')],['github','GitHub',()=>reachable('https://github.com/')],['youtube','YouTube Premium',youtube],['chatgpt','ChatGPT',chatgpt],['claude','Claude',claude],['gemini','Gemini',gemini],['netflix','Netflix',netflix],['disney','Disney+',disney],['prime','Prime Video',prime],['spotify','Spotify',spotify],['tiktok','TikTok',tiktok],['discord','Discord',discord],['bilibili','哔哩哔哩番剧',bilibili]];
  const selected=arg.profile==='all'?checks:checks.filter(x=>['github','chatgpt','claude','gemini'].includes(x[0]));
  const results=new Array(selected.length);let cursor=0;
  function report() {
    if(finished)return;finished=true;
    const lines=selected.map((x,i)=>{const r=results[i] || {status:'timeout'};return (r.status==='available'?'🟢':r.status==='timeout'||r.status==='failed'?'🔴':'🟠')+' '+x[1]+'：'+(labels[r.status]||'未知')+(r.region?' ['+r.region+']':'')+(r.delay?' · '+r.delay+' ms':'');});
    const content='路径：'+(route==='current'?'按当前 Loon 路由':route)+'\n'+lines.join('\n')+'\n检测完成：'+new Date().toISOString()+'\n地区结论来自上游规则推断；非登录、对话或播放实测。';
    $done({title:'常用服务检测',content});
  }
  const deadline=setTimeout(report,100000);
  async function worker(){while(cursor<selected.length && !finished){const i=cursor++;try{results[i]=await selected[i][2]();}catch(_){results[i]={status:'failed'};}}}
  Promise.all([worker(),worker(),worker(),worker()]).then(()=>{clearTimeout(deadline);report();});
})();
