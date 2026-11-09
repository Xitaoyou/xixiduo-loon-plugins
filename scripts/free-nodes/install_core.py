"""下载固定版本的官方检测核心并核对 GitHub 官方发布摘要。"""
import hashlib
import io
from pathlib import Path
import tarfile
from urllib.request import urlopen

VERSION = '1.14.4'
SHA256 = '699a1b510aa4396b2176d32d1181920399ebf1e267835da6f3b598d0f7c24968'
NAME = f'sing-box-{VERSION}-linux-amd64'


def main():
    with urlopen(f'https://github.com/SagerNet/sing-box/releases/download/v{VERSION}/{NAME}.tar.gz', timeout=60) as r:
        blob = r.read(64 * 1024 * 1024)
    if hashlib.sha256(blob).hexdigest() != SHA256:
        raise SystemExit('Proxy core checksum mismatch')
    # 只读取指定二进制，拒绝任意归档路径写入。
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as archive:
        entry = archive.getmember(NAME + '/sing-box')
        if not entry.isfile():
            raise SystemExit('Invalid core archive')
        binary = archive.extractfile(entry).read()
    path = Path('.runtime/sing-box')
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(binary)
    path.chmod(0o700)
    print('Verified sing-box ' + VERSION)


if __name__ == '__main__':
    main()
