#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inject_dylib.py 的离线自测：用合成的 Mach-O / IPA 夹具跑全流程，不需要真机或真样本。"""

import importlib.util
import os
import plistlib
import struct
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "tools", "inject_dylib.py")

spec = importlib.util.spec_from_file_location("inject_dylib", TOOL)
inj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inj)

passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + (" — " + detail if detail else ""))


def build_macho(nslices=1, text_off=0x4000, with_sig=True, encrypted=False, total=0x5000):
    """合成 Mach-O：__TEXT（fileoff=0，含一个 __text section）+ 可选 LC_CODE_SIGNATURE。"""
    def one_slice():
        cmds = b""
        # LC_SEGMENT_64 __TEXT
        seg = struct.pack("<II", 0x19, 72 + 80)
        seg += b"__TEXT".ljust(16, b"\0")
        seg += struct.pack("<QQQQ", 0x100000000, total, 0, total)
        seg += struct.pack("<IIII", 7, 5, 1, 0)
        sec = b"__text".ljust(16, b"\0") + b"__TEXT".ljust(16, b"\0")
        sec += struct.pack("<QQ", 0x100000000 + text_off, 0x100)
        sec += struct.pack("<IIIIIIII", text_off, 2, 0, 0, 0x80000400, 0, 0, 0)
        cmds += seg + sec
        if with_sig:
            cmds += struct.pack("<IIII", 0x1D, 16, total - 32, 32)
        if encrypted:
            cmds += struct.pack("<IIIIII", 0x2C, 24, 0x1000, 0x1000, 1, 0)
        ncmds = (1 if with_sig else 0) + (1 if encrypted else 0) + 1
        hdr = struct.pack("<IIIIIIII", 0xFEEDFACF, 0x0100000C, 0, 6, ncmds, len(cmds), 0x00200085, 0)
        body = bytearray(total)
        body[:32] = hdr
        body[32:32 + len(cmds)] = cmds
        return bytes(body)

    if nslices == 1:
        return one_slice()
    slices = [one_slice() for _ in range(nslices)]
    off0 = 0x4000
    fat_hdr = struct.pack(">II", 0xCAFEBABE, len(slices))
    offs = [off0]
    for i in range(1, len(slices)):
        offs.append(offs[-1] + len(slices[0]))
    for i, (s, o) in enumerate(zip(slices, offs)):
        fat_hdr += struct.pack(">iiIII", 0x0100000C, 0, o, len(s), 14)
    out = bytearray(offs[-1] + len(slices[-1]))
    out[:len(fat_hdr)] = fat_hdr
    for s, o in zip(slices, offs):
        out[o:o + len(s)] = s
    return bytes(out)


def build_ipa(tmp, macho, bundle="com.dazz.camera.vintagecamera", app_name="DazzCamera.app", exe="DazzCamera", base_name="work"):
    root = os.path.join(tmp, base_name)
    os.makedirs(root, exist_ok=True)
    appdir = os.path.join(root, "Payload", app_name)
    os.makedirs(appdir, exist_ok=True)
    with open(os.path.join(appdir, exe), "wb") as f:
        f.write(macho)
    with open(os.path.join(appdir, "Info.plist"), "wb") as f:
        plistlib.dump({"CFBundleIdentifier": bundle, "CFBundleExecutable": exe}, f)
    os.makedirs(os.path.join(appdir, "_CodeSignature"), exist_ok=True)
    with open(os.path.join(appdir, "_CodeSignature", "CodeResources"), "wb") as f:
        f.write(b"stale")
    ipa = os.path.join(tmp, base_name + ".ipa")
    with zipfile.ZipFile(ipa, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(os.path.join(tmp, base_name, "Payload")):
            for name in files:
                full = os.path.join(root, name)
                zf.write(full, os.path.relpath(full, os.path.join(tmp, base_name)))
    return ipa


print("build_macho fixture")

tmp = tempfile.mkdtemp(prefix="dzinject_test_")
try:
    dylib = os.path.join(tmp, "DazzPro.dylib")
    with open(dylib, "wb") as f:
        f.write(b"\xcf\xfa\xed\xfe" + b"\0" * 4092)

    # 1) thin：注入成功、文件不长大、签名命令被删
    print("1. thin 注入")
    thin = build_macho()
    p = os.path.join(tmp, "thin")
    with open(p, "wb") as f:
        f.write(thin)
    before = os.path.getsize(p)
    r = inj.patch_binary(p, inj.DEFAULT_LOAD_PATH, dry_run=False)
    after_data = open(p, "rb").read()
    check("返回一条 slice 结果", len(r) == 1, str(r))
    check("未跳过", not r[0].get("skipped"), str(r[0]))
    check("文件大小不变（原地打补丁）", len(after_data) == before)
    check("移除了 LC_CODE_SIGNATURE", r[0]["removed_code_signature"])
    ncmds, sizeofcmds = struct.unpack_from("<II", after_data, 16)
    check("ncmds 变成 2", ncmds == 2, str(ncmds))
    check("sizeofcmds 变大", sizeofcmds > 168, str(sizeofcmds))
    names = inj.existing_dylibs(after_data, 0, inj.walk_commands(after_data, 0)[2])
    check("LC_LOAD_DYLIB 指向 @executable_path", inj.DEFAULT_LOAD_PATH in names, str(names))
    check("原 __text section 偏移未变", struct.unpack_from("<I", after_data, 32 + 72 + 48)[0] == 0x4000)
    check("补丁后仍能解析 load command", inj.walk_commands(after_data, 0)[0] == 2)

    # 2) 重复注入被跳过
    print("2. 重复注入")
    r2 = inj.patch_binary(p, inj.DEFAULT_LOAD_PATH, dry_run=False)
    check("第二次注入跳过", r2[0].get("skipped") is True, str(r2[0]))

    # 3) dry-run 不落盘
    print("3. dry-run")
    p2 = os.path.join(tmp, "thin2")
    with open(p2, "wb") as f:
        f.write(build_macho())
    raw_before = open(p2, "rb").read()
    rd = inj.patch_binary(p2, inj.DEFAULT_LOAD_PATH, dry_run=True)
    check("dry-run 报告会注入", not rd[0].get("skipped"), str(rd[0]))
    check("dry-run 未改文件", open(p2, "rb").read() == raw_before)

    # 4) 头部空间不足要报错，而不是写坏文件
    print("4. 头部空间不足")
    tight = build_macho(text_off=32 + 168)  # 只剩 0 字节余量
    p3 = os.path.join(tmp, "tight")
    with open(p3, "wb") as f:
        f.write(tight)
    tight_before = open(p3, "rb").read()
    try:
        inj.patch_binary(p3, inj.DEFAULT_LOAD_PATH, dry_run=False)
        check("空间不足应报错", False)
    except SystemExit as e:
        check("空间不足报错退出", e.code == 1)
    check("报错时文件未被写坏", open(p3, "rb").read() == tight_before)

    # 5) 加密二进制要拦住
    print("5. FairPlay 加密拦停")
    p4 = os.path.join(tmp, "enc")
    with open(p4, "wb") as f:
        f.write(build_macho(encrypted=True))
    try:
        inj.patch_binary(p4, inj.DEFAULT_LOAD_PATH, dry_run=False)
        check("加密二进制应报错", False)
    except SystemExit as e:
        check("加密二进制报错退出", e.code == 1)

    # 6) fat 双 slice 都要注入
    print("6. fat 双架构")
    fat = build_macho(nslices=2)
    p5 = os.path.join(tmp, "fat")
    with open(p5, "wb") as f:
        f.write(fat)
    rf = inj.patch_binary(p5, inj.DEFAULT_LOAD_PATH, dry_run=False)
    check("两个 slice 都处理", len(rf) == 2, str(len(rf)))
    check("两个 slice 都注入成功", all(not x.get("skipped") for x in rf), str(rf))
    fat_after = open(p5, "rb").read()
    for off, size, ct in inj.macho_slices(fat_after):
        n = inj.walk_commands(fat_after, off)[0]
        check("slice@0x%x ncmds==2" % off, n == 2, str(n))
    check("fat 文件大小不变", len(fat_after) == len(fat))

    # 7) 端到端：IPA 进 → IPA 出
    print("7. IPA 端到端")
    ipa = build_ipa(tmp, build_macho(), base_name="dazz")
    out_ipa = os.path.join(tmp, "out.ipa")
    old_argv = sys.argv
    sys.argv = ["inject_dylib.py", "--ipa", ipa, "--dylib", dylib, "-o", out_ipa]
    try:
        inj.main()
    finally:
        sys.argv = old_argv
    check("生成了输出 IPA", os.path.isfile(out_ipa))
    with zipfile.ZipFile(out_ipa) as zf:
        names = zf.namelist()
        check("IPA 里有 Frameworks/DazzPro.dylib",
              "Payload/DazzCamera.app/Frameworks/DazzPro.dylib" in names, str(names))
        check("旧的 _CodeSignature 已删除",
              not any("_CodeSignature" in n for n in names), str(names))
        exe_bytes = zf.read("Payload/DazzCamera.app/DazzCamera")
        check("主可执行文件被注入", inj.DEFAULT_LOAD_PATH in
              inj.existing_dylibs(exe_bytes, 0, inj.walk_commands(exe_bytes, 0)[2]))
        for info in zf.infolist():
            check("zip 条目无绝对路径 " + info.filename, not info.filename.startswith("/"))

    # 8) 非 Dazz App 也能处理（工具本身与 bundle 无关，plist 决定）
    print("8. 其它 App 也能处理")
    ipa2 = build_ipa(tmp, build_macho(), bundle="com.example.other", app_name="Other.app", exe="Other", base_name="other")
    out2 = os.path.join(tmp, "out2.ipa")
    sys.argv = ["inject_dylib.py", "--ipa", ipa2, "--dylib", dylib, "-o", out2]
    try:
        inj.main()
    finally:
        sys.argv = old_argv
    with zipfile.ZipFile(out2) as zf:
        check("其它 App 也注入成功",
              "Payload/Other.app/Frameworks/DazzPro.dylib" in zf.namelist())
finally:
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

print("")
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
