# purref-reference-boards

English version: [README.en.md](README.en.md)

PureRef 2.x 形式のリファレンスボード（.pur）を PNG 画像から生成するための Muse カスタムスキルです。
生成したファイルは、Obsidian プラグイン「LazyRef PUR Viewer」のパーサーで開けることを確認してから渡す、という検証込みの手順になっています。

生成器は **Python 標準ライブラリのみ** で動作します（2026-11-21 に Rust 版から入れ替え）。Rust のビルドもテンプレート .pur も不要です。

## 中身

- `SKILL.md` / `skill.yaml` — スキル本体
- `SETUP.md` — 必要な環境とセットアップ手順
- `tools/gen_pur.py` / `tools/purcore.py` / `tools/template_data.py` — .pur 生成器（Python、本線）
- `tools/gen2x.rs` — 旧・Rust 版生成器（検証基準のリファレンス実装として同梱）
- `tools/check_pur.sh` / `tools/harness.mts` — パーサーチェック用

## 使い方

環境構築と使い方は [SETUP.md](SETUP.md) を参照してください。

## 依存

- 生成：Python 3.10 以上（標準ライブラリのみ）
- パーサー: LazyRef PUR Viewer（obsidian-pur-viewer）の parser 一式
- フォーマット実装の出自: LazyRef（purcore）: https://github.com/achrllrogia45/LazyRef
