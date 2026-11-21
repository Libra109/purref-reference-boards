#!/usr/bin/env python3
"""Build a PureRef 2.x .pur from a folder of PNGs — Python port of gen2x.rs.

Standard library only; no Rust, no fixture file at runtime (the golden
fixture's template values are baked into template_data.py).

Usage: gen_pur.py <input_dir> <output.pur>

Layout mirrors gen2x: images in filename order, placed left to right with a
20px gap, each item's transform centered on its image, image_transform set
per image to (-w/2, -h/2) so the bitmap exactly fills the centered bounds.
"""

import base64
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import purcore
import template_data as tpl

GAP = 20.0


def png_size(data: bytes):
    w = struct.unpack_from(">i", data, 16)[0]
    h = struct.unpack_from(">i", data, 20)[0]
    return w, h


def build_scene(in_dir: str) -> tuple[dict, bytes]:
    names = [n for n in os.listdir(in_dir)
             if os.path.splitext(n)[1] == ".png"
             and os.path.isfile(os.path.join(in_dir, n))]
    names.sort()  # same order as gen2x's sorted full paths (shared dir prefix)

    tw, th = float(tpl.TEMPLATE_IMAGE_WIDTH), float(tpl.TEMPLATE_IMAGE_HEIGHT)
    thumb = base64.b64decode(tpl.THUMBNAIL_B64)

    scene = {"images": [], "items": [], "items_images": [], "groups": [],
             "drawings": [], "notes": [], "metadata": None}
    x_cursor = 0.0
    total_w = 0.0
    max_h = 0.0

    for i, name in enumerate(names):
        with open(os.path.join(in_dir, name), "rb") as f:
            data = f.read()
        w, h = png_size(data)
        img_id = i

        scene["images"].append({
            "id": img_id, "width": w, "height": h,
            "checksum": purcore.md5_hex(data), "format": "PNG",
            "source": name, "source_type": 1, "origin": name, "data": data})

        transform = (1.0, 0.0, 0.0,
                     0.0, 1.0, 0.0,
                     x_cursor + w / 2.0, 0.0, 1.0)
        sort_order = {"num_sign": 1, "num_limbs": [i + 1],
                      "den_sign": 1, "den_limbs": [1]}
        item = {"id": img_id, "name": name, "transform": transform,
                "sort_order": sort_order}
        item.update(tpl.TEMPLATE_ITEM)  # z, opacity, parent, locked, comment
        scene["items"].append(item)

        elements = [(etype, x * (w / tw), y * (h / th))
                    for (etype, x, y) in tpl.TEMPLATE_BOUNDS["elements"]]
        bounds = {"elements": elements,
                  "c_start": tpl.TEMPLATE_BOUNDS["c_start"],
                  "fill_rule": tpl.TEMPLATE_BOUNDS["fill_rule"]}
        # The bitmap's top-left sits at (-w/2, -h/2) in item-local space so it
        # exactly fills the centered bounds. Copying the template's
        # image_transform verbatim would leave PureRef rendering the picture
        # misplaced inside a wrong-sized frame.
        image_transform = (1.0, 0.0, 0.0,
                           0.0, 1.0, 0.0,
                           -w / 2.0, -h / 2.0, 1.0)
        iimg = {"id": img_id, "image": img_id,
                "image_transform": image_transform, "image_bounds": bounds}
        iimg.update(tpl.TEMPLATE_ITEM_IMAGE)  # flags, playback_*
        scene["items_images"].append(iimg)

        x_cursor += w + GAP
        total_w = x_cursor - GAP
        max_h = max(max_h, float(h))
        print(f"added {name} {w}x{h}")

    meta = dict(tpl.TEMPLATE_METADATA)
    meta.update({
        "thumbnail": thumb,
        "last_load_checksum": None,
        "last_load_path": None,
        "last_save_path": None,
        "scene_rect": (0.0, -max_h / 2.0, total_w, max_h),
    })
    scene["metadata"] = meta
    return scene, thumb


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: gen_pur.py <input_dir> <output.pur>")
    in_dir, out_path = sys.argv[1], sys.argv[2]

    scene, thumb = build_scene(in_dir)
    pur_bytes = purcore.write_pur(scene, thumb)

    # atomic write like PurFile::write: temp file in the target dir, then rename
    tmp = os.path.join(os.path.dirname(os.path.abspath(out_path)),
                       f"{os.path.basename(out_path)}.{os.getpid()}.tmp")
    with open(tmp, "wb") as f:
        f.write(pur_bytes)
    os.replace(tmp, out_path)
    print(f"wrote {out_path}")

    # verify: read back with checksum verification on
    back = purcore.read_pur(pur_bytes, verify=True)
    print(f"read back: {len(back['images'])} images, {len(back['items'])} items")
    for im in back["images"]:
        print(f"  image {im['id']} {im['width']}x{im['height']} "
              f"{len(im['data'])} bytes format={im['format']!r} src={im['source']!r}")
    print(f"format detect: {purcore.detect_format(pur_bytes)}")
    print(f"checksum verify: {purcore.verify_checksum(pur_bytes)}")


if __name__ == "__main__":
    main()
