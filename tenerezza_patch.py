#!/usr/bin/env python3
"""Patch a Japanese Tenerezza Xbox ISO using the bundled xdelta files.

Place this script beside tools/ and xdeltas/. Run without arguments to find a
single input ISO beside the script, or supply an ISO path as the first argument.
Windows drag-and-drop uses that argument when .py files are associated with Python.
Only Python's standard library is required.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
OUTPUT_NAME = "Tenerezza (English).iso"

# SHA-256 of the original Japanese files in this project's source/ directory.
# Patches may change between releases; these identify the required retail input.
SOURCE_SHA256 = {
    "default.xbe": "a01e3d0cc50b7747e90201b5e1462a91c507c14d30e276b218a4fe415675e18e",
    "GPARTS.PAK": "552fd7994497df36a13f28866cb99194f78cb384a519b56043c675860e13d724",
    "SCRIPT.PAK": "16a16070271e8ab3b8c9ee35b602733d89aaae7ddc8ea7d2a93bdb3bd43c8f22",
}


class PatchError(Exception):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_index(directory: Path) -> dict[str, Path]:
    """Index immediate files by case-insensitive name, rejecting ambiguity."""
    result = {}
    for path in directory.iterdir():
        if path.is_file():
            key = path.name.casefold()
            if key in result:
                raise PatchError(f"Ambiguous filenames: {result[key]} and {path}")
            result[key] = path
    return result


def find_iso(root: Path, argument: str | None) -> Path:
    if argument:
        iso = Path(argument).expanduser().resolve()
        if not iso.is_file() or iso.suffix.casefold() != ".iso":
            raise PatchError(f"Input ISO does not exist or is not an .iso file: {iso}")
    else:
        candidates = sorted(p for p in root.iterdir() if p.is_file()
                            and p.suffix.casefold() == ".iso"
                            and p.name.casefold() != OUTPUT_NAME.casefold())
        if len(candidates) != 1:
            names = ", ".join(p.name for p in candidates) or "none"
            raise PatchError("Expected one input ISO beside the script "
                             f"(found {len(candidates)}: {names}). Supply an ISO path explicitly.")
        iso = candidates[0].resolve()
    if iso == (root / OUTPUT_NAME).resolve():
        raise PatchError("The English output ISO cannot also be the input ISO.")
    return iso


def find_tools(root: Path) -> tuple[Path, Path]:
    directory = root / "tools"
    if not directory.is_dir():
        raise PatchError(f"Missing tools directory: {directory}")
    files = file_index(directory)
    xdelta = files.get("xdelta.exe")
    # Distribution spelling requested by the patch package; also accept the
    # upstream spelling already used by this repository's build.py.
    xiso = files.get("extractxiso.exe") or files.get("extract-xiso.exe")
    missing = []
    if xdelta is None:
        missing.append("tools/xdelta.exe")
    if xiso is None:
        missing.append("tools/extractxiso.exe (or tools/extract-xiso.exe)")
    if missing:
        raise PatchError("Missing required tools:\n  " + "\n  ".join(missing))
    return xdelta, xiso


def find_patches(root: Path) -> dict[str, Path]:
    directory = root / "xdeltas"
    if not directory.is_dir():
        raise PatchError(f"Missing patch directory: {directory}")
    files = file_index(directory)
    expected = {name.casefold() + ".xdelta" for name in SOURCE_SHA256}
    errors = [f"Missing patch: {name}.xdelta" for name in SOURCE_SHA256
              if name.casefold() + ".xdelta" not in files]
    errors.extend(f"Unexpected patch: {path.name}" for key, path in files.items()
                  if key.endswith(".xdelta") and key not in expected)
    if errors:
        raise PatchError("Patch filenames do not match this release:\n  " + "\n  ".join(errors))
    return {name: files[name.casefold() + ".xdelta"] for name in SOURCE_SHA256}


def validate_source(source: Path) -> dict[str, Path]:
    files = file_index(source)
    matched = {}
    errors = []
    for name, expected in SOURCE_SHA256.items():
        path = files.get(name.casefold())
        if path is None:
            errors.append(f"Missing source file (name checked without case): {name}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            errors.append(f"SHA-256 mismatch: {path.name}\n"
                          f"    expected: {expected}\n    actual:   {actual}")
        else:
            matched[name] = path
            print(f"  Verified {path.name}", flush=True)
    if errors:
        raise PatchError("Source validation failed; no patches were applied:\n  " + "\n  ".join(errors))
    return matched


def run(command: list[str], root: Path) -> None:
    print("> " + subprocess.list2cmdline(command), flush=True)
    result = subprocess.run(command, cwd=root, check=False)
    if result.returncode:
        raise PatchError(f"{Path(command[0]).name} failed with exit code {result.returncode}.")


def patch_game(root: Path, argument: str | None, overwrite: bool = False) -> Path:
    iso = find_iso(root, argument)
    xdelta, xiso = find_tools(root)
    patches = find_patches(root)
    source = root / "source"
    output = root / OUTPUT_NAME
    # Never delete an existing extraction (particularly the development project's
    # clean source/). Failed attempts can be inspected before the user moves it.
    if source.is_symlink() or (source.exists() and
                              (not source.is_dir() or any(source.iterdir()))):
        raise PatchError(f"{source} already exists and is not an empty directory. "
                         "Move it elsewhere before running this script; it will not be deleted.")
    if output.exists() and not overwrite:
        raise PatchError(f"Output already exists: {output}\n"
                         "Use --overwrite to replace the output ISO.")

    print(f"Input: {iso}\nExtracting ISO into {source}", flush=True)
    source_created = not source.exists()
    source.mkdir(exist_ok=True)
    run([str(xiso), "-x", "-d", str(source), str(iso)], root)
    print("Checking original filenames and SHA-256 hashes...", flush=True)
    matched = validate_source(source)

    # Decode every file successfully before replacing any extracted original.
    # xdelta supplies its own target checksum validation during decoding.
    with tempfile.TemporaryDirectory(prefix=".tenerezza_patch-", dir=root) as work:
        temporary = Path(work)
        for name, patch in patches.items():
            print(f"Patching {name}...", flush=True)
            target = temporary / name
            run([str(xdelta), "-d", "-s", str(matched[name]), str(patch), str(target)], root)
            if not target.is_file() or target.stat().st_size == 0:
                raise PatchError(f"xdelta did not create a nonempty patched file: {name}")
        for name, original in matched.items():
            os.replace(temporary / name, original)

        print("Creating English ISO...", flush=True)
        temporary_iso = temporary / OUTPUT_NAME
        run([str(xiso), "-c", str(source), str(temporary_iso)], root)
        if not temporary_iso.is_file() or temporary_iso.stat().st_size == 0:
            raise PatchError("extract-xiso did not create a nonempty output ISO.")
        os.replace(temporary_iso, output)
    if source_created:
        # Delete only our extraction, after the finished ISO is safely in place.
        # Verify the resolved target before recursively removing anything.
        if source.is_symlink() or source.resolve() != root.resolve() / "source":
            raise PatchError(f"Refusing to clean an unexpected source path: {source}")
        print(f"Removing extracted files: {source}", flush=True)
        shutil.rmtree(source)
    print(f"Patch complete: {output}", flush=True)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", nargs="?", help="Japanese ISO path; otherwise find one beside this script")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing English output ISO")
    parser.add_argument("--pause", action="store_true", help="wait for Enter before closing (useful on Windows)")
    args = parser.parse_args(argv)
    try:
        patch_game(ROOT, args.iso, args.overwrite)
        status = 0
    except (PatchError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        status = 1
    except KeyboardInterrupt:
        print("\nPatching interrupted.", file=sys.stderr)
        status = 130
    if args.pause and sys.stdin.isatty():
        input("Press Enter to close...")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
