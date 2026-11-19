# purref-reference-boards

PureRef 2.x 形式のリファレンスボード（.pur）を PNG 画像から生成するための Muse カスタムスキルです。
生成したファイルは、Obsidian プラグイン「LazyRef PUR Viewer」のパーサーで開けることを確認してから渡す、という検証込みの手順になっています。

## 中身

- `SKILL.md` / `skill.yaml` — スキル本体
- `SETUP.md` — 必要な環境とセットアップ手順
- `tools/gen2x.rs` — .pur 生成器（LazyRef の purcore を使う Rust 製 example）
- `tools/check_pur.sh` / `tools/harness.mts` — パーサーチェック用

## 使い方

環境構築と使い方は [SETUP.md](SETUP.md) を参照してください。

## 依存

- LazyRef（purcore）: https://github.com/achrllrogia45/LazyRef
- パーサー: LazyRef PUR Viewer（obsidian-pur-viewer）の parser 一式
