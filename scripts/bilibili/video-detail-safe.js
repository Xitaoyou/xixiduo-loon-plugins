/*
 * Bilibili video detail ad filter, byte-preserving Protobuf patcher for Loon.
 * Standalone implementation based on field numbers observed in kokoryh's
 * Bilibili protobuf response handler (2026-09-06).
 * Preserve all unknown fields and untouched byte slices in original order;
 * do NOT decode/encode the entire video-detail reply.
 * Inspired by upstream: https://github.com/Moli-X/Tool/tree/X/Loon/Plugin/Kelee
 */
(function (root) {
  "use strict";
  var MAX_BODY = 24 * 1024 * 1024;
  var MAX_FIELDS = 200000;
  var REMOVABLE_MODULES = {18: true, 29: true, 55: true};

  function varint(buf, start, end) {
    var value = 0, factor = 1, pos = start, b;
    for (var i = 0; i < 10 && pos < end; i++) {
      b = buf[pos++];
      if (i < 8) value += (b & 127) * factor;
      if (!(b & 128)) return {value: value, end: pos};
      factor *= 128;
    }
    throw new Error("Invalid or truncated varint");
  }

  function fields(buf) {
    var result = [], pos = 0;
    while (pos < buf.length) {
      if (result.length >= MAX_FIELDS) throw new Error("Too many fields");
      var start = pos, tag = varint(buf, pos, buf.length);
      pos = tag.end;
      var field = Math.floor(tag.value / 8), wire = tag.value % 8;
      if (field === 0 || field > 536870911) throw new Error("Invalid protobuf field");
      var valueStart = pos, valueEnd = pos;
      if (wire === 0) {
        pos = varint(buf, pos, buf.length).end;
        valueEnd = pos;
      } else if (wire === 1) {
        pos += 8;
        valueEnd = pos;
      } else if (wire === 2) {
        var length = varint(buf, pos, buf.length);
        valueStart = length.end;
        pos = valueStart + length.value;
        valueEnd = pos;
      } else if (wire === 5) {
        pos += 4;
        valueEnd = pos;
      } else {
        throw new Error("Unsupported protobuf wire type " + wire);
      }
      if (pos > buf.length) throw new Error("Truncated protobuf field");
      result.push({field: field, wire: wire, start: start,
        tagEnd: tag.end, valueStart: valueStart,
        valueEnd: valueEnd, end: pos});
    }
    return result;
  }

  function encodeVarint(n) {
    var result = [];
    do {
      var b = n % 128;
      n = Math.floor(n / 128);
      result.push(n ? b | 128 : b);
    } while (n);
    return new Uint8Array(result);
  }

  function concat(parts) {
    var size = 0;
    parts.forEach(function (p) { size += p.length; });
    var dest = new Uint8Array(size), pos = 0;
    parts.forEach(function (p) { dest.set(p, pos); pos += p.length; });
    return dest;
  }

  function patch(buf, editor) {
    var list = fields(buf), parts = [], changed = false;
    list.forEach(function (f) {
      var replacement = editor(f, buf);
      if (replacement === undefined) parts.push(buf.subarray(f.start, f.end));
      else if (replacement === null) changed = true;
      else { parts.push(replacement); changed = true; }
    });
    return changed ? concat(parts) : buf;
  }

  function nested(f, buf, handler) {
    if (f.wire !== 2) return undefined;
    var body = buf.subarray(f.valueStart, f.valueEnd);
    var edited = handler(body);
    if (edited === body) return undefined;
    // Keep the original tag bytes; only replace this nested length and content.
    return concat([buf.subarray(f.start, f.tagEnd), encodeVarint(edited.length), edited]);
  }

  function smallNumber(buf, f) {
    return f.wire === 0 ? varint(buf, f.valueStart, f.valueEnd).value : null;
  }

  // Old video API: field 28 inside Relate is an advertising payload.
  function legacyRelateIsAd(buf) {
    return fields(buf).some(function (f) {
      return f.field === 28 && f.wire === 2 && f.valueEnd > f.valueStart;
    });
  }

  // New video API: do not strip AI_RECOMMEND (7) or ordinary AV (1) cards.
  function uniteRelateIsAd(buf) {
    var fs = fields(buf), type = null, hasAdStock = false, hasUniqueId = false;
    fs.forEach(function (f) {
      if (f.field === 1) type = smallNumber(buf, f);
      if (f.field === 11 && f.wire === 2 && f.valueEnd > f.valueStart) hasAdStock = true;
      if (f.field === 12 && f.wire === 2) {
        var base = buf.subarray(f.valueStart, f.valueEnd);
        hasUniqueId = hasUniqueId || fields(base).some(function (b) {
          return b.field === 6 && b.wire === 2 && b.valueEnd > b.valueStart;
        });
      }
    });
    return type === 5 || type === 4 || type === 11 || hasAdStock || hasUniqueId;
  }

  function relatedCards(buf) {
    return patch(buf, function (f, b) {
      if (f.field === 1 && f.wire === 2 &&
          uniteRelateIsAd(b.subarray(f.valueStart, f.valueEnd))) return null;
    });
  }

  function moduleAdType(buf) {
    var list = fields(buf);
    for (var i = 0; i < list.length; i++) {
      if (list[i].field === 1) {
        var n = smallNumber(buf, list[i]);
        return !!REMOVABLE_MODULES[n];
      }
    }
    return false;
  }

  function moduleBody(buf) {
    return patch(buf, function (f, b) {
      if (f.field === 22) return nested(f, b, relatedCards);
    });
  }

  function introTab(buf) {
    return patch(buf, function (f, b) {
      if (f.field !== 2 || f.wire !== 2) return;
      var module = b.subarray(f.valueStart, f.valueEnd);
      if (moduleAdType(module)) return null;
      return nested(f, b, moduleBody);
    });
  }

  function tabModule(buf) {
    return patch(buf, function (f, b) {
      if (f.field === 2) return nested(f, b, introTab);
    });
  }

  function mainTab(buf) {
    return patch(buf, function (f, b) {
      if (f.field === 1) return nested(f, b, tabModule);
    });
  }

  function viewUnite(buf) {
    return patch(buf, function (f, b) {
      if (f.field === 7 && f.wire === 2) return null; // Top-level CM
      if (f.field === 5) return nested(f, b, mainTab);
    });
  }

  function oldView(buf) {
    return patch(buf, function (f, b) {
      if ([30, 31, 41, 50].indexOf(f.field) >= 0 && f.wire === 2) return null;
      if (f.field === 10 && f.wire === 2 &&
          legacyRelateIsAd(b.subarray(f.valueStart, f.valueEnd))) return null;
    });
  }

  function oldRelatesFeed(buf) {
    return patch(buf, function (f, b) {
      if (f.field === 1 && f.wire === 2 &&
          legacyRelateIsAd(b.subarray(f.valueStart, f.valueEnd))) return null;
    });
  }

  function uniteRelatesFeed(buf) {
    return patch(buf, function (f, b) {
      if (f.field === 1 && f.wire === 2 &&
          uniteRelateIsAd(b.subarray(f.valueStart, f.valueEnd))) return null;
    });
  }

  function asyncModules(buf) {
    return patch(buf, function (f, b) {
      if (f.field !== 1 || f.wire !== 2) return;
      var module = b.subarray(f.valueStart, f.valueEnd);
      if (moduleAdType(module)) return null;
      return nested(f, b, moduleBody);
    });
  }

  function aiRelateAsync(buf) {
    return patch(buf, function (f, b) {
      if (f.field === 1 && f.wire === 2) return null; // CM blob
      if (f.field === 2) return nested(f, b, asyncModules);
    });
  }

  function method(url) {
    var part = String(url || "").split("?")[0];
    if (/\/bilibili\.app\.view\.v1\.View\/View$/i.test(part)) return oldView;
    if (/\/bilibili\.app\.viewunite\.v1\.View\/View$/i.test(part)) return viewUnite;
    if (/\/bilibili\.app\.view\.v1\.View\/RelatesFeed$/i.test(part)) return oldRelatesFeed;
    if (/\/bilibili\.app\.viewunite\.v1\.View\/RelatesFeed$/i.test(part)) return uniteRelatesFeed;
    if (/\/bilibili\.app\.viewunite\.v1\.View\/AIRelateAsync$/i.test(part)) return aiRelateAsync;
    return null;
  }

  function processBody(body, url, ungzip) {
    var handle = method(url);
    if (!handle || !(body instanceof Uint8Array) || body.length < 5 || body.length > MAX_BODY) return body;
    // gRPC envelope: [compressed flag:1][size:4 big endian][protobuf].
    if (body[0] !== 0 && body[0] !== 1) return body;
    var len = ((body[1] * 16777216) + (body[2] << 16) + (body[3] << 8) + body[4]);
    if (len !== body.length - 5) return body; // Do not touch streams or unknown frames.
    var proto = body.subarray(5);
    if (body[0] === 1) {
      if (typeof ungzip !== "function") return body;
      proto = ungzip(proto);
      if (!(proto instanceof Uint8Array)) return body;
    }
    var changed = handle(proto);
    if (changed === proto) return body;
    var out = new Uint8Array(changed.length + 5);
    out[0] = 0;
    var n = changed.length;
    out[1] = (n >>> 24) & 255;
    out[2] = (n >>> 16) & 255;
    out[3] = (n >>> 8) & 255;
    out[4] = n & 255;
    out.set(changed, 5);
    return out;
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {varint: varint, fields: fields, encodeVarint: encodeVarint,
      concat: concat, processBody: processBody, method: method,
      viewUnite: viewUnite, oldView: oldView, uniteRelatesFeed: uniteRelatesFeed};
  }
  if (typeof $done === "function") {
    try {
      var input = $response && $response.body;
      var output = processBody(input, $request && $request.url,
        typeof $utils !== "undefined" && typeof $utils.ungzip === "function"
          ? function (z) { return $utils.ungzip(z); } : null);
      if (output !== input) $done({body: output});
      else $done({});
    } catch (err) {
      console.log("[Bilibili safe detail] Keep original response: " + err);
      $done({});
    }
  }
})(this);
