#!/usr/bin/env python3
"""
Verifies the 4 manual hooks required by ReSukiSU on a 4.14 non-GKI kernel
(stat, execveat, faccessat, reboot) are present with the correct call
signature before the build proceeds. Exits 1 with a clear message on any
missing or mismatched hook, so CI fails fast instead of at link time.

Usage:
    python3 verify_ksu_hooks.py \
        --dfd fs/stat.c \
        --execveat fs/exec.c \
        --faccessat fs/open.c \
        --reboot kernel/reboot.c
"""
import argparse
import re
import sys

# Each check: (label, required substring pattern, human hint on failure)
CHECKS = {
    "dfd": [
        (
            "stat hook (3-arg, with flags)",
            re.compile(r"ksu_handle_stat\s*\(\s*&dfd\s*,\s*&filename\s*,\s*&flags\s*\)"),
            "expected ksu_handle_stat(&dfd, &filename, &flags) — "
            "if this still says 2 args, re-apply resukisu-cepheus-manual-hooks.patch",
        ),
    ],
    "execveat": [
        (
            "execveat hook",
            re.compile(r"ksu_handle_execveat\s*\("),
            "ksu_handle_execveat(...) call not found in fs/exec.c",
        ),
    ],
    "faccessat": [
        (
            "faccessat hook",
            re.compile(r"ksu_handle_faccessat\s*\("),
            "ksu_handle_faccessat(...) call not found in fs/open.c",
        ),
    ],
    "reboot": [
        (
            "reboot hook",
            re.compile(r"ksu_handle_sys_reboot\s*\("),
            "ksu_handle_sys_reboot(...) call not found in kernel/reboot.c",
        ),
    ],
    "setresuid": [
        (
            "setresuid hook (SuSFS Inline Hook requirement)",
            re.compile(r"ksu_handle_setresuid\s*\("),
            "ksu_handle_setresuid(...) call not found in kernel/sys.c — "
            "re-apply resukisu-inline-hook-fixups.patch",
        ),
    ],
    "sys_read": [
        (
            "sys_read hook (SuSFS Inline Hook requirement)",
            re.compile(r"ksu_handle_sys_read\s*\("),
            "ksu_handle_sys_read(...) call not found in fs/read_write.c — "
            "re-apply resukisu-inline-hook-fixups.patch",
        ),
    ],
    "input_event": [
        (
            "input_event hook (SuSFS Inline Hook requirement)",
            re.compile(r"ksu_handle_input_handle_event\s*\("),
            "ksu_handle_input_handle_event(...) call not found in drivers/input/input.c — "
            "re-apply resukisu-inline-hook-fixups.patch",
        ),
    ],
}


def check_file(arg_name: str, path: str) -> list[str]:
    errors = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError as e:
        return [f"[{arg_name}] could not open {path}: {e}"]

    for label, pattern, hint in CHECKS[arg_name]:
        if not pattern.search(content):
            errors.append(f"[{arg_name}] {path}: missing {label} — {hint}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dfd", required=True, help="path to fs/stat.c")
    parser.add_argument("--execveat", required=True, help="path to fs/exec.c")
    parser.add_argument("--faccessat", required=True, help="path to fs/open.c")
    parser.add_argument("--reboot", required=True, help="path to kernel/reboot.c")
    parser.add_argument("--setresuid", required=True, help="path to kernel/sys.c")
    parser.add_argument("--sys-read", dest="sys_read", required=True, help="path to fs/read_write.c")
    parser.add_argument("--input-event", dest="input_event", required=True, help="path to drivers/input/input.c")
    args = parser.parse_args()

    all_errors = []
    all_errors += check_file("dfd", args.dfd)
    all_errors += check_file("execveat", args.execveat)
    all_errors += check_file("faccessat", args.faccessat)
    all_errors += check_file("reboot", args.reboot)
    all_errors += check_file("setresuid", args.setresuid)
    all_errors += check_file("sys_read", args.sys_read)
    all_errors += check_file("input_event", args.input_event)

    if all_errors:
        print("::error::Manual hook verification failed:")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("[+] All 4 required manual hooks verified present with correct signatures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
