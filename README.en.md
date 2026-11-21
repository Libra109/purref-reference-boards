# purref-reference-boards

A Muse custom skill that builds PureRef 2.x reference boards (.pur) from PNG images — instead of handing reference images over one by one, the skill generates a single .pur board and verifies it opens in the parser of the Obsidian plugin "LazyRef PUR Viewer" before delivery.

The generator runs on the **Python standard library only** (switched from the Rust implementation on 2026-11-21). No Rust build, no template .pur file needed at runtime.

## Contents

- `SKILL.md` / `skill.yaml` — the skill itself
- `SETUP.md` — requirements and setup (Japanese)
- `tools/gen_pur.py` / `tools/purcore.py` / `tools/template_data.py` — the .pur generator (Python, mainline)
- `tools/gen2x.rs` — the original Rust generator, kept as the reference implementation the Python port was verified against
- `tools/check_pur.sh` / `tools/harness.mts` — parser check tooling

## Quick start

```sh
# put PNG files only in a folder, then:
python3 tools/gen_pur.py <input_folder> <output.pur>
```

Images are laid out in a single row in filename order with a 20px gap. After writing, the generator reads the file back with its container checksum verified and prints the image count and sizes.

## Requirements

- Generation: Python 3.10+ (standard library only)
- Parser check (optional): Node.js 20+ and the parser from LazyRef PUR Viewer (obsidian-pur-viewer) — see SETUP.md

## Verification

The Python generator was differentially tested against the Rust reference: byte-identical output on real boards (3 images) and on a single-image board, and structurally identical output on an odd-size 7-image board (the only byte differences were stale bytes in unused SQLite page space; the logical content is identical). All generated boards pass the plugin parser check with zero warnings.

One honest caveat: the parser renders by width/height, so it cannot detect misplaced images. Final visual confirmation in genuine PureRef is recommended — see the notes in SETUP.md.

## Origin

The .pur format implementation derives from LazyRef (purcore): https://github.com/achrllrogia45/LazyRef

Japanese README: [README.md](README.md)
