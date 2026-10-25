#!/usr/bin/env python3
"""Package app/ into a webOS .ipk without ares-cli.

An .ipk is a GNU ar archive holding debian-binary, control.tar.gz and
data.tar.gz, laid out the same way ares-package does it. A Homebrew Channel
manifest for the release is written next to it.
"""
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(ROOT, "app")
DIST_DIR = os.path.join(ROOT, "dist")
REPO_URL = "https://github.com/hamedafra/filimo-webos"
RAW_URL = "https://raw.githubusercontent.com/hamedafra/filimo-webos/main"
MTIME = int(time.time())


def tar_gz(entries):
    """entries: list of (arcname, bytes or None for a directory)."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.mtime = MTIME
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            if data is None:
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            else:
                info.mode = 0o644
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return gzip.compress(raw.getvalue(), mtime=MTIME)


def ar(members):
    out = io.BytesIO()
    out.write(b"!<arch>\n")
    for name, data in members:
        # dpkg-style member names (no trailing "/"), readable by opkg and BSD ar.
        header = "%-16s%-12d%-6d%-6d%-8s%-10d`\n" % (name, MTIME, 0, 0, "100644", len(data))
        out.write(header.encode("ascii"))
        out.write(data)
        if len(data) % 2:
            out.write(b"\n")
    return out.getvalue()


def main():
    with open(os.path.join(APP_DIR, "appinfo.json")) as f:
        appinfo = json.load(f)
    app_id, version = appinfo["id"], appinfo["version"]

    app_prefix = "./usr/palm/applications/%s/" % app_id
    pkg_prefix = "./usr/palm/packages/%s/" % app_id
    data = [("./", None), ("./usr/", None), ("./usr/palm/", None),
            ("./usr/palm/applications/", None), (app_prefix, None),
            ("./usr/palm/packages/", None), (pkg_prefix, None)]

    size = 0
    for dirpath, dirnames, filenames in os.walk(APP_DIR):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        rel = os.path.relpath(dirpath, APP_DIR)
        if rel != ".":
            data.append((app_prefix + rel + "/", None))
        for fn in sorted(filenames):
            if fn.startswith("."):
                continue
            with open(os.path.join(dirpath, fn), "rb") as f:
                content = f.read()
            size += len(content)
            arc = fn if rel == "." else rel + "/" + fn
            data.append((app_prefix + arc, content))

    packageinfo = json.dumps({
        "app": app_id,
        "id": app_id,
        "loc_name": appinfo.get("title", app_id),
        "package_format_version": 2,
        "vendor": appinfo.get("vendor", ""),
        "version": version,
    }, indent=2).encode()
    data.append((pkg_prefix + "packageinfo.json", packageinfo))
    size += len(packageinfo)

    control = (
        "Package: %s\n"
        "Version: %s\n"
        "Section: misc\n"
        "Priority: optional\n"
        "Architecture: all\n"
        "Installed-Size: %d\n"
        "Maintainer: N/A <nobody@example.com>\n"
        "Description: %s\n"
        "webOS-Package-Format-Version: 2\n"
        "webOS-Packager-Version: 1.0.0\n"
    ) % (app_id, version, max(1, size // 1024), appinfo.get("title", app_id))

    ipk = ar([
        ("debian-binary", b"2.0\n"),
        ("control.tar.gz", tar_gz([("./", None), ("./control", control.encode())])),
        ("data.tar.gz", tar_gz(data)),
    ])

    os.makedirs(DIST_DIR, exist_ok=True)
    ipk_name = "%s_%s_all.ipk" % (app_id, version)
    out_path = os.path.join(DIST_DIR, ipk_name)
    with open(out_path, "wb") as f:
        f.write(ipk)
    print(out_path)

    # ipkUrl is resolved relative to the manifest, so both go in the same release.
    manifest = {
        "id": app_id,
        "version": version,
        "type": appinfo["type"],
        "title": appinfo.get("title", app_id),
        "iconUri": RAW_URL + "/app/largeIcon.png",
        "sourceUrl": REPO_URL,
        "rootRequired": False,
        "ipkUrl": ipk_name,
        "ipkHash": {"sha256": hashlib.sha256(ipk).hexdigest()},
    }
    manifest_path = os.path.join(DIST_DIR, "%s.manifest.json" % app_id)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(manifest_path)


if __name__ == "__main__":
    sys.exit(main())
