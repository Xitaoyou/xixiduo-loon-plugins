// DazzPro —— 在设备本地解锁 Dazz（Dazz相机 / com.dazz.camera.vintagecamera）的 Pro 权益
//
// ── 为什么 Loon 插件做不到 ────────────────────────────────────────────
// Dazz 2.18 的会员判定全在设备本地（对主二进制取证所得）：
//   · StoreKit 2：遍历 Transaction.currentEntitlements + VerificationResult 校验；
//   · 本地缓存：DazzStoreKitPersistence（键 DazzStoreKitTransactionsKey，队列
//     com.dazzstorekit.persistence.queue，方法 setTransactionsDictionary(_:) /
//     StoreKitGetValue(key:) / StoreKitSetValue(value:key:)）；
//   · 主二进制的网络域名只有 Firebase / AdMob / Apple / CloudFront 素材，
//     没有自有会员 API、没有 RevenueCat、没有服务端 verifyReceipt。
// HTTP 层没有可改的响应，所以 Loon / Surge / QX 结构上无效（抓包空白即为此因）。
//
// ── 本插件做什么 ───────────────────────────────────────────────────────
// 运行时把「本地门控的布尔结果」固定成会员态：
//   L1  无参、返回 BOOL 的 getter：强词命中 → YES（试用/欠费词 → NO）；
//   L2  AntiDetector 的落盘动作 applyTamper(reason:persistFlag:fromBootstrap:) 置空，
//       避免注入被记成 jailbreak_detected 触发降级；
//   L3  dumpMode：只打印候选方法（类名 + 选择子 + 返回类型），不改任何东西，
//       用于 App 升级后重新定位门控点。
//
// 能力边界（照实写）：ObjC 暴露出来的那层门控可以直接换 IMP；Swift 原生直调的方法
// 不在 ObjC 方法列表里，需要按符号偏移做 inline hook，得先用 dumpMode 拿到实机日志。

#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#import <os/log.h>

static os_log_t gDZLog = NULL;
static NSUInteger gDZHit = 0;

static BOOL dz_yes(id self, SEL _cmd) { (void)self; (void)_cmd; return YES; }
static BOOL dz_no(id self, SEL _cmd) { (void)self; (void)_cmd; return NO; }

static void dz_nop6(id self, SEL _cmd, id a, BOOL b, BOOL c) {
    (void)self; (void)_cmd; (void)a; (void)b; (void)c;
    os_log(gDZLog, "tamper suppressed");
}

// 强词：出现即认定是会员态，允许在任何 Dazz 自有类上生效
static const char *kStrong[] = {
    "Pro", "Vip", "VIP", "Premium", "Purchased", "Subscribed", "Subscription",
    "Unlocked", "Entitled", "Entitlement", "Lifetime", "Forever", "Membership"
};
// 弱词：需要类名也落在购买/会员相关类里才动
static const char *kWeak[] = { "Purchase", "Member", "Paid", "Bought", "Restore", "Unlock", "Yearly" };
// 试用/欠费：命中即 NO
static const char *kOff[] = { "Trial", "TrialExpired", "NeedPay", "NeedPurchase", "NeedBuy", "Expired" };

// 不能碰：硬件能力 / 进度 / 事件上报
static const char *kDeny[] = {
    "isAppleProRAWEnabled", "isAppleProRAWSupported", "isAppleProRawCaptureEnabled",
    "isAppleProRAWPixelFormat", "isProgressive", "isProxy", "isPurchaseEvent",
    "isEcommercePurchaseEvent", "hasOwnProperty", "hasProperty", "isMemberOfClass",
    "isPSMRequestInProgress", "isProgressiveSbSgv", "canAuthenticateAgainstProtectionSpace"
};

// 购买/会员相关类（弱词在这里才生效）
static const char *kBuyClass[] = {
    "Pro", "Purchas", "StoreKit", "Product", "Vip", "VIP", "Member", "Entitle",
    "Subscri", "Premium", "Paywall", "Buy", "Advertise", "Promot", "Store"
};

#define DZ_LEN(x) (sizeof(x) / sizeof((x)[0]))

// 静态链进主二进制的第三方类
static BOOL dz_thirdParty(const char *n) {
    if (n == NULL) return YES;
    if (strncmp(n, "_TtC", 4) == 0) return NO;   // Swift 类，形如 _TtC10DazzCamera15DazzProCard
    if (strncmp(n, "DZ", 2) == 0 || strncmp(n, "Dazz", 4) == 0) return NO;
    static const char *pfx[] = { "FIR", "GUL", "GTD", "GDTC", "SD", "APM", "CLS", "NAD",
                                 "FBL", "FIA", "RCN", "GCK", "NS", "UI", "AV", "CA", "SK", "__" };
    for (size_t i = 0; i < DZ_LEN(pfx); i++)
        if (strncmp(n, pfx[i], strlen(pfx[i])) == 0) return YES;
    return NO;
}

// 按驼峰切词后逐词精确比对：isProActive → is / Pro / Active
static BOOL dz_tokenHit(const char *sel, const char **tokens, size_t n) {
    if (sel == NULL || *sel == 0) return NO;
    char buf[256];
    size_t len = strlen(sel);
    if (len >= sizeof(buf)) len = sizeof(buf) - 1;
    memcpy(buf, sel, len); buf[len] = 0;
    char *p = buf;
    while (*p) {
        char *start = p;
        if (*p >= 65 && *p <= 90) {
            p++;
            while (*p >= 65 && *p <= 90) p++;
            while (*p >= 97 && *p <= 122) p++;
        } else {
            while (*p && (*p < 65 || *p > 90)) p++;
        }
        if (p == start) { p++; continue; }
        char save = *p; *p = 0;
        BOOL hit = NO;
        for (size_t i = 0; i < n; i++) if (strcmp(start, tokens[i]) == 0) { hit = YES; break; }
        *p = save;
        if (hit) return YES;
    }
    return NO;
}

static BOOL dz_classHit(const char *cls) {
    if (cls == NULL) return NO;
    for (size_t i = 0; i < DZ_LEN(kBuyClass); i++)
        if (strstr(cls, kBuyClass[i]) != NULL) return YES;
    return NO;
}

// 否定子串：出现这些片段的 selector 一律不碰（硬件能力 / 进度 / 事件 / 保护 / 处理流程）
static const char *kForbidSubs[] = {
    "RAW", "ProRes", "Progress", "Property", "Protect", "Process", "Proxy", "Promot",
    "Event", "Purpose", "Apple", "StoreKitVersion", "Receipt", "PurchaseHistory"
};

static BOOL dz_forbidden(const char *sel) {
    if (sel == NULL) return YES;
    for (size_t i = 0; i < DZ_LEN(kForbidSubs); i++)
        if (strstr(sel, kForbidSubs[i]) != NULL) return YES;
    return NO;
}

static BOOL dz_isBOOL(const char *t) { return t != NULL && (t[0] == 66 || t[0] == 99); }

static void dz_patchClass(Class cls, BOOL dumpOnly) {
    const char *cname = class_getName(cls);
    BOOL buyCls = dz_classHit(cname);
    for (int meta = 0; meta <= 1; meta++) {
        unsigned int n = 0;
        Method *ms = class_copyMethodList(meta ? object_getClass(cls) : cls, &n);
        if (ms == NULL) continue;
        for (unsigned int i = 0; i < n; i++) {
            const char *sel = sel_getName(method_getName(ms[i]));
            if (sel == NULL || strchr(sel, ':') != NULL) continue;   // 只要无参 getter
            char type[16] = { 0 };
            method_getReturnType(ms[i], type, sizeof(type));
            BOOL off = dz_tokenHit(sel, kOff, DZ_LEN(kOff));
            BOOL on = !off && (dz_tokenHit(sel, kStrong, DZ_LEN(kStrong)) ||
                        (buyCls && dz_tokenHit(sel, kWeak, DZ_LEN(kWeak))));
            if (!on && !off) continue;
            BOOL denied = dz_forbidden(sel);
            for (size_t d = 0; d < DZ_LEN(kDeny); d++) if (strcmp(sel, kDeny[d]) == 0) denied = YES;
            if (denied) continue;
            if (dumpOnly) {
                os_log(gDZLog, "cand %{public}s %{public}s [%{public}s] want=%{public}s",
                       cname, sel, type, off ? "NO" : "YES");
                continue;
            }
            if (!dz_isBOOL(type)) continue;
            IMP want = off ? (IMP)dz_no : (IMP)dz_yes;
            if (method_getImplementation(ms[i]) == want) continue;
            method_setImplementation(ms[i], want);
            gDZHit++;
            os_log(gDZLog, "patch %{public}s %{public}s = %{public}s", cname, sel, off ? "NO" : "YES");
        }
        free(ms);
    }
}

static void dz_patchTamper(Class cls) {
    Method m = class_getInstanceMethod(cls, sel_registerName("applyTamper(reason:persistFlag:fromBootstrap:)"));
    if (m == NULL) return;
    if (method_getImplementation(m) == (IMP)dz_nop6) return;
    method_setImplementation(m, (IMP)dz_nop6);
    os_log(gDZLog, "patch tamper %{public}s", class_getName(cls));
}

static void dz_sweep(BOOL dumpOnly) {
    unsigned int count = 0;
    Class *list = objc_copyClassList(&count);
    if (list == NULL) return;
    NSUInteger before = gDZHit;
    for (unsigned int i = 0; i < count; i++) {
        Class cls = list[i];
        const char *img = class_getImageName(cls);
        if (img == NULL || strstr(img, "DazzCamera") == NULL) continue;   // 只动主二进制
        const char *nm = class_getName(cls);
        if (dz_thirdParty(nm)) continue;
        if (!dumpOnly) dz_patchTamper(cls);
        dz_patchClass(cls, dumpOnly);
    }
    free(list);
    if (!dumpOnly && gDZHit != before)
        NSLog(@"[DazzPro] patched +%lu (total %lu)", (unsigned long)(gDZHit - before), (unsigned long)gDZHit);
}

__attribute__((constructor)) static void dz_init(void) {
    @autoreleasepool {
        gDZLog = os_log_create("com.xitaoyou.dazzpro", "main");
        NSString *bid = [[NSBundle mainBundle] bundleIdentifier];
        if (bid == nil || ![bid hasPrefix:@"com.dazz"]) {
            os_log(gDZLog, "skip bundle %{public}s", bid.UTF8String ?: "(nil)");
            return;
        }
        BOOL dump = [[NSUserDefaults standardUserDefaults] boolForKey:@"DazzProDump"];
        NSLog(@"[DazzPro] loaded %@ dump=%d", bid, (int)dump);
        for (int r = 0; r < 8; r++) {   // 类按需 realize，分几轮补扫
            int64_t d = (int64_t)(0.5 * NSEC_PER_SEC * (r + 1));
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW, d), dispatch_get_main_queue(), ^{
                dz_sweep(dump);
            });
        }
    }
}