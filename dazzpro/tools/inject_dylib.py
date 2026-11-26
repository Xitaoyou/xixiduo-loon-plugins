#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 DazzPro.dylib 注入未加密的 Dazz IPA，产出可直接自签安装的 IPA。

不需要越狱：只做两件事——
  1. 给主可执行文件加一条 LC_LOAD_DYLIB（@executable_path/Frameworks/DazzPro.dylib），
     顺手删掉 LC_CODE_SIGNATURE（重签会重新生成）；
  2. 把 DazzPro.dylib 拷进 Payload/xxx.app/Frameworks/，删掉旧的 _CodeSignature/。

之后再拿 zsign / Sideloadly / AltStore 重签就行。

用法:
    python inject_dylib.py --ipa Dazz_decrypted.ipa --dylib DazzPro.dylib -o DazzPro.ipa
    python inject_dylib.py --ipa Dazz_decrypted.ipa --dylib DazzPro.dylib -o out.ipa --dry-run
"""

import argparse
import os
import plistlib
import shutil
import struct
import sys
import tempfile
import zipfile

MH_MAGIC_64 = 0xFEEDFACF
FAT_MAGIC = 0xCAFEBABE
FAT_MAGIC_64 = 0xCAFEBABF
LC_SEGMENT_64 = 0x19
LC_CODE_SIGNATURE = 0x1D
LC_LOAD_DYLIB = 0xC
LC_LOAD_WEAK_DYLIB = 0x8000001C
LC_REEXPORT_DYLIB = 0x8000001F
LC_ENCRYPTION_INFO_64 = 0x2C

DEFAULT_LOAD_PATH = "@executable_path/Frameworks/DazzPro.dylib"


def die(msg):
    sys.stderr.write("错误: " + msg + "\n")
    raise SystemExit(1)


def macho_slices(data):
    """返回 [(offset, size, cputype)]；thin 只有一个。"""
    magic = struct.unpack(">I", data[:4])[0]
    out = []
    if magic in (FAT_MAGIC, FAT_MAGIC_64):
        n = struct.unpack(">I", data[4:8])[0]
        p = 8
        for _ in range(n):
            if magic == FAT_MAGIC:
                cputype, cpusub, off, size, align = struct.unpack(">iiIII", data[p:p + 20])
                p += 20
            else:
                cputype, cpusub, off, size, align, res = struct.unpack(">iiQQII", data[p:p + 32])
                p += 32
            out.append((off, size, cputype))
    else:
        out.append((0, len(data), None))
    return out


def walk_commands(buf, base):
    magic = struct.unpack_from("<I", buf, base)[0]
    if magic != MH_MAGIC_64:
        die("不是 64 位 Mach-O（magic=0x%08x）" % magic)
    ncmds, sizeofcmds = struct.unpack_from("<II", buf, base + 16)
    end = base + 32 + sizeofcmds
    p = base + 32
    cmds = []
    while p < end:
        cmd, cmdsize = struct.unpack_from("<II", buf, p)
        if cmdsize < 8 or p + cmdsize > end:
            die("load command 越界（偏移 0x%x）" % p)
        cmds.append((cmd, p, cmdsize))
        p += cmdsize
    return ncmds, sizeofcmds, cmds


def first_section_offset(buf, base, cmds):
    """__TEXT(fileoff==0) 里第一个有内容 section 的文件偏移，即头部可用空间的右边界。"""
    best = None
    for cmd, p, size in cmds:
        if cmd != LC_SEGMENT_64:
            continue
        fileoff = struct.unpack_from("<Q", buf, p + 40)[0]
        if fileoff != 0:
            continue
        nsects = struct.unpack_from("<I", buf, p + 64)[0]
        for i in range(nsects):
            s = p + 72 + i * 80
            if s + 80 > p + size:
                break
            sec_size = struct.unpack_from("<Q", buf, s + 40)[0]
            sec_off = struct.unpack_from("<I", buf, s + 48)[0]
            if sec_size == 0 or sec_off == 0:
                continue
            if best is None or sec_off < best:
                best = sec_off
    return best


def make_dylib_cmd(path):
    raw = path.encode("utf-8") + b"\0"
    raw += b"\0" * ((-(24 + len(raw))) % 8)
    cmdsize = 24 + len(raw)
    return struct.pack("<IIIIII", LC_LOAD_DYLIB, cmdsize, 24, 2, 0x10000, 0x10000) + raw


def existing_dylibs(buf, base, cmds):
    names = []
    for cmd, p, size in cmds:
        if cmd not in (LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB, LC_REEXPORT_DYLIB):
            continue
        name_off = struct.unpack_from("<I", buf, p + 8)[0]
        s = p + name_off
        e = s
        while buf[e] != 0:
            e += 1
        names.append(bytes(buf[s:e]).decode("utf-8", "replace"))
    return names


def is_encrypted(buf, base, cmds):
    for cmd, p, size in cmds:
        if cmd != LC_ENCRYPTION_INFO_64:
            continue
        cryptid = struct.unpack_from("<I", buf, p + 16)[0]
        if cryptid != 0:
            return True
    return False


def inject_slice(buf, base, size, load_path):
    """原地改一个 slice 的头部：删 LC_CODE_SIGNATURE，加 LC_LOAD_DYLIB。"""
    ncmds, sizeofcmds, cmds = walk_commands(buf, base)
    if is_encrypted(buf, base, cmds):
        die("主二进制仍带 FairPlay 加密（LC_ENCRYPTION_INFO_64 cryptid!=0），先砸壳拿到解密后的 IPA")
    if load_path in existing_dylibs(buf, base, cmds):
        return {"skipped": True, "reason": "已存在同名 LC_LOAD_DYLIB"}
    keep = []
    removed_sig = False
    for cmd, p, csize in cmds:
        if cmd == LC_CODE_SIGNATURE:
            removed_sig = True
            continue
        keep.append(bytes(buf[p:p + csize]))
    new_blob = b"".join(keep) + make_dylib_cmd(load_path)
    limit = first_section_offset(buf, base, cmds)
    if limit is None:
        limit = 32 + len(new_blob)
    avail = limit - 32
    if len(new_blob) > avail:
        die("头部空间不足：需要 %d 字节，只剩 %d 字节（原始 sizeofcmds=%d）" % (len(new_blob), avail, sizeofcmds))
    struct.pack_into("<II", buf, base + 16, len(keep) + 1, len(new_blob))
    buf[base + 32:base + 32 + len(new_blob)] = new_blob
    pad = limit - 32 - len(new_blob)
    if pad > 0:
        buf[base + 32 + len(new_blob):base + limit] = b"\0" * pad
    return {"skipped": False, "ncmds": len(keep) + 1, "used": len(new_blob), "avail": avail,
            "removed_code_signature": removed_sig}


def patch_binary(path, load_path, dry_run):
    with open(path, "rb") as f:
        data = bytearray(f.read())
    results = []
    for off, size, cputype in macho_slices(bytes(data)):
        results.append(inject_slice(data, off, size, load_path))
    if dry_run:
        return results
    with open(path, "wb") as f:
        f.write(bytes(data))
    return results


def find_app(tmpdir):
    payload = os.path.join(tmpdir, "Payload")
    if not os.path.isdir(payload):
        die("IPA 里没有 Payload/ 目录")
    apps = [d for d in os.listdir(payload) if d.endswith(".app")]
    if not apps:
        die("Payload/ 下没有 .app")
    return os.path.join(payload, apps[0])


def zip_dir(src, out_path):
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, src)
                info = zipfile.ZipInfo(rel)
                mode = os.stat(full).st_mode
                info.external_attr = (0o100644 if not (mode & 0o111) else 0o100755) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(full, "rb") as f:
                    zf.writestr(info, f.read())


def main():
    ap = argparse.ArgumentParser(description="给 Dazz IPA 注入 DazzPro.dylib（免越狱路线）")
    ap.add_argument("--ipa", required=True, help="已砸壳（解密）的 Dazz IPA")
    ap.add_argument("--dylib", required=True, help="DazzPro.dylib 路径")
    ap.add_argument("-o", "--output", required=True, help="输出 IPA 路径")
    ap.add_argument("--load-path", default=DEFAULT_LOAD_PATH, help="注入的 LC_LOAD_DYLIB 路径")
    ap.add_argument("--dry-run", action="store_true", help="只检查不改文件")
    args = ap.parse_args()

    if not os.path.isfile(args.ipa):
        die("找不到 IPA: " + args.ipa)
    if not os.path.isfile(args.dylib):
        die("找不到 dylib: " + args.dylib)

    tmpdir = tempfile.mkdtemp(prefix="dazzinject_")
    try:
        with zipfile.ZipFile(args.ipa) as zf:
            zf.extractall(tmpdir)
        app = find_app(tmpdir)
        with open(os.path.join(app, "Info.plist"), "rb") as f:
            info = plistlib.load(f)
        exe_name = info.get("CFBundleExecutable")
        if not exe_name:
            die("Info.plist 里没有 CFBundleExecutable")
        exe = os.path.join(app, exe_name)
        if not os.path.isfile(exe):
            die("可执行文件不存在: " + exe)
        print("App      : " + os.path.basename(app))
        print("Bundle   : " + str(info.get("CFBundleIdentifier")))
        print("Exe      : " + exe_name + " (%d 字节)" % os.path.getsize(exe))

        results = patch_binary(exe, args.load_path, args.dry_run)
        for r in results:
            if r.get("skipped"):
                print(" Mach-O  : 跳过（" + r["reason"] + "）")
            else:
                print(" Mach-O  : 已注入 LC_LOAD_DYLIB，ncmds=%d，头部用 %d/%d 字节，%s" % (
                    r["ncmds"], r["used"], r["avail"],
                    "已移除 LC_CODE_SIGNATURE" if r["removed_code_signature"] else "无 LC_CODE_SIGNATURE"))
        if args.dry_run:
            print("dry-run：未写入任何文件")
            return

        fw = os.path.join(app, "Frameworks")
        os.makedirs(fw, exist_ok=True)
        dest = os.path.join(fw, os.path.basename(args.dylib))
        shutil.copy2(args.dylib, dest)
        print(" dylib   : " + os.path.relpath(dest, tmpdir) + " (%d 字节)" % os.path.getsize(dest))

        sigdir = os.path.join(app, "_CodeSignature")
        if os.path.isdir(sigdir):
            shutil.rmtree(sigdir)
            print(" 签名    : 已删除旧的 _CodeSignature/（重签会重新生成）")

        plug = os.path.join(app, "PlugIns")
        if os.path.isdir(plug):
            for d in os.listdir(plug):
                sd = os.path.join(plug, d, "_CodeSignature")
                if os.path.isdir(sd):
                    shutil.rmtree(sd)

        zip_dir(tmpdir, args.output)
        print("输出     : " + args.output + " (%d 字节)" % os.path.getsize(args.output))
        print("")
        print("下一步（三选一）:")
        print("  1) zsign 自签：zsign -k cert.p12 -p 密码 -m app.mobileprovision -o signed.ipa " + args.output)
        print("  2) Sideloadly / AltStore / SideStore 直接安装 " + args.output)
        print("  3) 有 TrollStore 的话：TrollFools 里导入 IPA + DazzPro.dylib（这条根本不用本脚本）")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
