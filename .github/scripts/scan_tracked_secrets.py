"""Fail CI on obvious credential literals in tracked, non-binary files."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATTERNS = (
    re.compile(r"nvapi-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |PGP )?PRIVATE KEY-----"),
)
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".pdf", ".lock"}
TEST_SENTINELS = {"sk-this-must-not-persist"}


def main() -> int:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    findings: list[str] = []
    for relative in filter(None, tracked):
        path = ROOT / relative
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        matches = [match.group(0) for pattern in PATTERNS for match in pattern.finditer(text)]
        if any(match not in TEST_SENTINELS for match in matches):
            findings.append(relative)
    if findings:
        raise SystemExit("Credential literal scan failed: " + ", ".join(findings))
    print("Tracked-file credential literal scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
