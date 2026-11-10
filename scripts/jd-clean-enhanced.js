/*
 * JD Clean Enhanced | 2026-11-10
 * Independent response cleaner with the Base64 compatibility approach from
 * zbsdsb/loon-adblock-plugins (MIT); prior ideas: RuCu6/Maasea/kelee.
 * Does not distribute code from kelee.one. No telemetry or remote calls.
 */
(function () {
  var url=($request && $request.url)||"";
  var original=$response && $response.body;
  if (!/^https:\/\/api\.m\.jd\.com\/client\.action(?:\?|$)/i.test(url) ||
      typeof original!=="string" || !original || original.length>2000000) return $done({});

  var a=(typeof $argument==="object" && $argument)||{};
  var opt={
    splash:a.block_splash!==false,
    floating:a.block_floating!==false,
    popup:a.block_popup!==false,
    simplify:a.simplify_page!==false,
    compact:a.compact_tools===true
  };

  var alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  function b64Decode(str) {
    var s=str.replace(/\s/g,"").replace(/=+$/,""), buffer=0,bits=0,bytes=[],idx;
    for(var i=0;i<s.length;i++) {
      idx=alphabet.indexOf(s[i]); if(idx<0) return null;
      buffer=(buffer<<6)|idx;bits+=6;
      if(bits>=8){bits-=8;bytes.push((buffer>>bits)&255);}
    }
    var binary="";
    for(var j=0;j<bytes.length;j+=8192)
      binary+=String.fromCharCode.apply(null,bytes.slice(j,j+8192));
    try{return decodeURIComponent(escape(binary));}catch(e){return null;}
  }
  function b64Encode(str) {
    var bytes=unescape(encodeURIComponent(str)),i=0,out="",x,y,z;
    while(i<bytes.length) {
      x=bytes.charCodeAt(i++);
      y=i<bytes.length?bytes.charCodeAt(i++):-1;
      z=i<bytes.length?bytes.charCodeAt(i++):-1;
      out+=alphabet[x>>2]+alphabet[((x&3)<<4)|(y<0?0:y>>4)];
      out+=y<0?"=":alphabet[((y&15)<<2)|(z<0?0:z>>6)];
      out+=z<0?"=":alphabet[z&63];
    }
    return out;
  }

  function findFunction() {
    var m=/(?:\?|&)functionId=([\w]+)/.exec(url);
    if(m)return m[1];
    var body=$request && $request.body;
    if(typeof body!=="string"||body.length>40000)return "";
    m=/(?:^|[&?,"'\s])functionId["']?\s*[:=]\s*["']?([a-z]\w*)/i.exec(body);
    if(m)return m[1];
    if(body.length%4===0 && /^[A-Za-z0-9+/=]+$/.test(body)) {
      var decoded=b64Decode(body);
      if(decoded){
        m=/(?:^|[&?,"'\s])functionId["']?\s*[:=]\s*["']?([a-z]\w*)/i.exec(decoded);
        if(m)return m[1];
      }
    }
    return "";
  }
  var fn=findFunction();
  if(/^(basicConfig|appConfig|deviceConfig)$/i.test(fn))return $done({});
  var obj,isB64=false,s=original.trim();
  try{obj=JSON.parse(s);}catch(e){
    if(s.length%4!==0||!/^[A-Za-z0-9+/=]+$/.test(s))return $done({});
    var decoded=b64Decode(s);
    if(!decoded)return $done({});
    try{obj=JSON.parse(decoded);isB64=true;}catch(err){return $done({});}
  }
  if(!obj||typeof obj!=="object"||Array.isArray(obj))return $done({});

  var homeTypes={bottomXview:1,float:1,photoCeiling:1,ruleFloat:1,
    searchIcon:1,topRotate:1,tabBarAtmosphere:1};
  var promoFloors={banner:1,jdDeliveryBanner:1,bannerFloor:1,
    bpDynamicFloor:1,plusFloor:1,bigSaleFloor:1,buyOften:1,
    newAttentionCard:1,newBigSaleFloor:1,newStyleAttentionCard:1,
    newsFloor:1,noticeFloor:1,recommendfloor:1};
  var keepTools=["applezhushou","lingjindouxin","dongdongnongchangxin",
    "chongwangwang","kehufuwu","xianzhiguanjia","wenyisheng",
    "jijianfuwu","zhuanzuanhongbao","huanletaojin"];
  var changed=false;
  function del(o,k) {
    if(o && Object.prototype.hasOwnProperty.call(o,k)){delete o[k];changed=true;}
  }
  function empty(o,k) {
    if(Array.isArray(o[k]) && o[k].length){o[k]=[];changed=true;}
  }
  function cleanPopupAndFloat(o) {
    if(!o||typeof o!=="object")return;
    if(opt.popup){
      del(o,"commonPopup");del(o,"commonPopup_dynamic");
      empty(o,"commonWindows");empty(o,"commonTips");
    }
    if(opt.floating)del(o,"floatLayer");
  }
  function cleanFloors(p) {
    if(!Array.isArray(p.floors))return;
    if(opt.simplify){
      var n=p.floors.length;
      p.floors=p.floors.filter(function(f){
        return !f||typeof f!=="object"||!promoFloors[f.mId];
      });
      if(p.floors.length!==n)changed=true;
    }
    p.floors.forEach(function(f){
      if(!f||!f.data||typeof f.data!=="object")return;
      var d=f.data;
      if(f.mId==="basefloorinfo")cleanPopupAndFloat(d);
      if(f.mId==="userinfo"&&opt.simplify)del(d,"newPlusBlackCard");
      if(f.mId==="orderIdFloor"&&opt.simplify&&d.commentRemindInfo)
        empty(d.commentRemindInfo,"infos");
      if(f.mId==="iconToolFloor"&&opt.compact&&Array.isArray(d.nodes)){
        d.nodes.forEach(function(group,index){
          if(!Array.isArray(group))return;
          var filtered=group.filter(function(item){
            return item && keepTools.indexOf(item.functionId)!==-1;
          }).sort(function(x,y){
            return keepTools.indexOf(x.functionId)-keepTools.indexOf(y.functionId);
          });
          if(JSON.stringify(filtered)!==JSON.stringify(group)){
            d.nodes[index]=filtered;changed=true;
          }
        });
      }
    });
  }
  function clean(p) {
    if(!p||typeof p!=="object"||Array.isArray(p))return;
    var isSplash=/^(start|startup)$/i.test(fn) ||
      Object.prototype.hasOwnProperty.call(p,"showTimesDaily") ||
      Object.prototype.hasOwnProperty.call(p,"splashTime") ||
      Object.prototype.hasOwnProperty.call(p,"splashInterval");
    if(opt.splash && isSplash && Array.isArray(p.images)){
      empty(p,"images");
      if(p.showTimesDaily!==undefined&&p.showTimesDaily!==0){
        p.showTimesDaily=0;changed=true;
      }
    }
    var home=Array.isArray(p.floorList)||Array.isArray(p.webViewFloorList);
    if(opt.floating&&Array.isArray(p.floorList)){
      var n=p.floorList.length;
      p.floorList=p.floorList.filter(function(f){
        return !f||typeof f!=="object"||!homeTypes[f.type];
      });
      if(p.floorList.length!==n)changed=true;
    }
    if(opt.simplify&&home)empty(p,"webViewFloorList");
    if(home)cleanPopupAndFloat(p);
    if(Array.isArray(p.floors)){
      cleanFloors(p);cleanPopupAndFloat(p);
    }
    if(opt.simplify&&p.result&&typeof p.result==="object"&&
      (/^getTabHomeInfo$/i.test(fn) ||
       (Object.prototype.hasOwnProperty.call(p.result,"roofTop")&&
        Object.prototype.hasOwnProperty.call(p.result,"iconInfo")))){
      del(p.result,"roofTop");del(p.result,"iconInfo");
    }
    if(opt.simplify&&
      (/^(deliverLayer|orderTrackBusiness)$/i.test(fn)||Array.isArray(p.floors)))
      del(p,"bannerInfo");
  }
  try{
    clean(obj);
    if(obj.data&&typeof obj.data==="object"){
      clean(obj.data);
      if(obj.data.result&&typeof obj.data.result==="object")clean(obj.data.result);
    }
    if(obj.result&&typeof obj.result==="object")clean(obj.result);
    if(!changed)return $done({});
    return $done({body:isB64?b64Encode(JSON.stringify(obj)):JSON.stringify(obj)});
  }catch(e){return $done({});}
})();