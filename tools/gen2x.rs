//! PoC: build a brand-new PureRef 2.x .pur from a folder of PNGs, from scratch,
//! using the golden fixture scene as a structural template.
use purcore::blobs::{BigRational, QPainterPath, QRectF, QTransform, PathElement};
use purcore::model::{Image, Item, Scene};
use purcore::purfile::PurFile;
use std::path::Path;

fn png_size(bytes: &[u8]) -> (i32, i32) {
    let w = i32::from_be_bytes(bytes[16..20].try_into().unwrap());
    let h = i32::from_be_bytes(bytes[20..24].try_into().unwrap());
    (w, h)
}

fn md5_hex(data: &[u8]) -> String {
    purcore::checksum::md5_hex(data)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let fixture = Path::new(&args[1]);
    let in_dir = Path::new(&args[2]);
    let out = Path::new(&args[3]);

    let pf = PurFile::new(std::env::temp_dir().join("purcore-gen2x"));
    let template: Scene = pf.read(fixture, true);
    let t_item = template.items[0].clone();
    let t_iimg = template.items_images[0].clone();
    let t_bounds: QPainterPath = t_iimg.image_bounds.clone().unwrap();
    // template image size drives the bounds scaling (fixture is 64x48,
    // bounds are centered on origin)
    let (tw, th) = (
        template.images[0].width.unwrap() as f64,
        template.images[0].height.unwrap() as f64,
    );
    let thumb = purcore::container::extract_thumbnail(&std::fs::read(fixture).unwrap());

    let mut files: Vec<_> = std::fs::read_dir(in_dir)
        .unwrap()
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map(|x| x == "png").unwrap_or(false))
        .collect();
    files.sort();

    let mut scene = Scene::default();
    let mut x_cursor = 0.0f64;
    let gap = 20.0f64;
    let mut total_w = 0.0f64;
    let mut max_h = 0.0f64;

    for (i, path) in files.iter().enumerate() {
        let data = std::fs::read(path).unwrap();
        let (w, h) = png_size(&data);
        let fname = path.file_name().unwrap().to_string_lossy().to_string();
        let id = i as i64;

        scene.images.push(Image {
            id,
            width: Some(w),
            height: Some(h),
            checksum: Some(md5_hex(&data)),
            format: Some("PNG".to_string()),
            source: Some(fname.clone()),
            source_type: Some(1),
            origin: Some(fname.clone()),
            data: Some(data),
        });

        let transform = QTransform {
            m11: 1.0, m12: 0.0, m13: 0.0,
            m21: 0.0, m22: 1.0, m23: 0.0,
            m31: x_cursor + w as f64 / 2.0, m32: 0.0, m33: 1.0,
        };
        let sort = BigRational {
            num_sign: 1,
            num_limbs: vec![(i + 1) as u32],
            den_sign: 1,
            den_limbs: vec![1],
        };
        scene.items.push(Item {
            transform: Some(transform),
            sort_order: Some(sort),
            name: Some(fname.clone()),
            ..t_item.clone()
        });
        scene.items[i].id = id;

        let elements: Vec<PathElement> = t_bounds
            .elements
            .iter()
            .map(|e| PathElement {
                r#type: e.r#type,
                x: e.x * (w as f64 / tw),
                y: e.y * (h as f64 / th),
            })
            .collect();
        let mut iimg = t_iimg.clone();
        iimg.id = id;
        iimg.image = Some(id);
        // The bitmap's top-left sits at (-w/2, -h/2) in item-local space so
        // it exactly fills the centered bounds. Cloning the template's
        // image_transform verbatim leaves it at the template's small offset
        // and PureRef then renders the picture misplaced inside a
        // wrong-sized frame.
        iimg.image_transform = Some(QTransform {
            m11: 1.0, m12: 0.0, m13: 0.0,
            m21: 0.0, m22: 1.0, m23: 0.0,
            m31: -(w as f64) / 2.0, m32: -(h as f64) / 2.0, m33: 1.0,
        });
        iimg.image_bounds = Some(QPainterPath {
            elements,
            c_start: t_bounds.c_start,
            fill_rule: t_bounds.fill_rule,
        });
        scene.items_images.push(iimg);

        x_cursor += w as f64 + gap;
        total_w = x_cursor - gap;
        max_h = max_h.max(h as f64);
        println!("added {fname} {w}x{h}");
    }

    let mut meta = template.metadata.clone().unwrap();
    meta.thumbnail = Some(thumb.clone());
    meta.last_load_checksum = None;
    meta.last_load_path = None;
    meta.last_save_path = None;
    meta.scene_rect = Some(QRectF { x: 0.0, y: -max_h / 2.0, w: total_w, h: max_h });
    scene.metadata = Some(meta);

    pf.write(&scene, out, &thumb);
    println!("wrote {}", out.display());

    // verify: read back with checksum verification on
    let back: Scene = pf.read(out, true);
    println!("read back: {} images, {} items", back.images.len(), back.items.len());
    for im in &back.images {
        println!("  image {} {}x{} {} bytes format={:?} src={:?}",
            im.id, im.width.unwrap(), im.height.unwrap(),
            im.data.as_ref().unwrap().len(), im.format, im.source);
    }
    let bytes = std::fs::read(out).unwrap();
    println!("format detect: {:?}", purcore::container::detect_format(&bytes));
    println!("checksum verify: {}", purcore::container::verify_checksum(&bytes));
}
