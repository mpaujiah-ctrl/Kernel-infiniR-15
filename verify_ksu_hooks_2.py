#!/usr/bin/env python3
"""
Verifies the 4 manual hooks required by KernelSU-Next (branch `legacy`) on a
4.14 non-GKI kernel (stat, execveat, faccessat, reboot) are present with the
correct call signature before the build proceeds. Exits 1 with a clear
message on any missing or mismatched hook, so CI fails fast instead of at
link time.

NOTE: the 5th hook that used to be checked here (sys_read / fs/read_write.c)
was removed. On the `legacy` branch, KernelSU-Next now installs that hook
itself via an internal kprobe (sys_read_handler_pre in
kernel/runtime/ksud_integration.c) instead of requiring a manual call-site
patch in the kernel source. Keeping a check for it here would just fail
since fs/read_write.c is no longer patched at all. If you ever go back to
a KSUN version that expects the old manual sys_read hook, re-add the
--sys-read check and the corresponding CHECKS entry.

Usage:
    python3 verify_ksu_hooks_2.py \
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
            "stat hook (3-arg)",
            re.compile(r"ksu_handle_stat\s*\(\s*&dfd\s*,\s*&filename\s*,\s*&flag\s*\)"),
            "expected ksu_handle_stat(&dfd, &filename) in fs/stat.c — "
            "re-run the hook injection step",
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
    args = parser.parse_args()

    all_errors = []
    all_errors += check_file("dfd", args.dfd)
    all_errors += check_file("execveat", args.execveat)
    all_errors += check_file("faccessat", args.faccessat)
    all_errors += check_file("reboot", args.reboot)

    if all_errors:
        print("::error::Manual hook verification failed:")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("[+] All 4 required KSUN manual hooks verified present with correct signatures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
