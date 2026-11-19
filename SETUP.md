# purref_reference_boards — 環境とセットアップ

Muse のカスタムスキル「purref_reference_boards」の配布パッケージです。
画像資料を1枚ずつ渡す代わりに、PureRef 2.x 形式の .pur リファレンスボードとして生成し、パーサーで開けることを確認してから渡す、という作業手順（スキル本体）と、その実行に必要な環境・道具一式をまとめています。

## パッケージの中身

| ファイル | 内容 |
|---|---|
| `SKILL.md` / `skill.yaml` | スキル本体（Muse 用の手順書） |
| `tools/gen2x.rs` | .pur 生成器。LazyRef の purcore を使う Rust 製 example で、LazyRef 本体には含まれない自作物 |
| `tools/check_pur.sh` | 生成した .pur のパーサーチェック用ラッパースクリプト |
| `tools/harness.mts` | プラグインのパーサー（parsePur）をコマンドラインから呼ぶハーネス |

## 必要な環境

- **Rust ツールチェーン**（rustup 推奨）：gen2x のビルド用
- **Node.js 20 以上と npm**：パーサーチェック用（tsx で TypeScript を直接実行する）
- **git**：下記の取得用

### 外部から取得するもの

- **LazyRef**（.pur の読み書きライブラリ purcore を含む）：https://github.com/achrllrogia45/LazyRef
- **パーサー**：Obsidian プラグイン「LazyRef PUR Viewer」（Libra109/obsidian-pur-viewer）の parser 一式（parser.ts ほか）。チェック環境の構築に使う。代替として、本家 PureRef 2.x で実際に開いて確認する方法でもよい

## セットアップ

1. LazyRef を clone する
2. `tools/gen2x.rs` を `LazyRef/crates/purcore/examples/gen2x.rs` にコピーする
3. ビルドする：`cd LazyRef && cargo build --release --example gen2x`
   （バイナリは `target/release/examples/gen2x` にできる）
4. 生成のテンプレートには、LazyRef 同梱の `crates/purcore/tests/fixtures/S1_redbar-new.pur` を使う
5. パーサーチェック環境を作る
   - プラグインのパーサー一式をフォルダ（例：`plugin-test/`）に置き、`tools/harness.mts` を同じフォルダに入れる
   - そのフォルダで npm パッケージを入れる：`tsx`（^4.20.0）、`spark-md5`（^3.0.2）、`sql.js`（^1.14.1）
   - `tools/check_pur.sh` は、自分の置いた `plugin-test/` フォルダへ cd して harness を実行する作り。配置に合わせてパスを調整する
   - 作者環境では HEIC 対応が不要だったため heic.ts をスタブに差し替えてある。PNG のみのボードなら HEIC デコードは不要
6. スキルとして使う場合：このフォルダ一式を自分の Muse の `workspace/custom-skills/` に置く。**SKILL.md 内のパスは作者環境のものなので、自分の配置に合わせて書き換えること**

## 使い方

1. 入力フォルダに **PNG だけ**を入れる（ファイル名順に横一列、間隔 20px で並ぶ）
2. 生成する：
   `gen2x <フィクスチャ.pur> <入力フォルダ> <出力.pur>`
3. チェックする：
   `check_pur.sh <出力.pur>`
   出力の version・画像数・各画像のサイズ・warnings を確認する。**warnings がゼロ**であることと、**画像数が入力した PNG の数と一致する**ことが合格条件
4. 仕上げに本家 PureRef でも開いて表示を確認する（下記の注意点のとおり、表示位置のずれはパーサーだけでは検出できない）

## ハマりどころ（検証済みの注意点）

- **入力は PNG のみ**。他形式のファイルは黙って除外されるので、JPG などは先に PNG へ変換しておく
- **テンプレートに素材ボードの .pur を使わない**。枠が二重に拡大され、PureRef で画像が異常に大きく表示される。必ず素のフィクスチャ（S1_redbar-new.pur）を使う
- **表示位置は image_transform で決まる**。PureRef は image_bounds（枠）と image_transform（左上オフセット）で表示位置を決める。テンプレートの transform（-32, -24）を複製すると全画像がずれるため、画像ごとに `(-w/2, -h/2)` を設定する（同梱の gen2x.rs はこの修正を適用済み）
- **旧形式（1.x）の生成器は使わない**。コンテナ 2.1 専用のパーサーでは開けない。2.x 形式で生成すること
- **パーサーのチェックだけでは位置ずれに気づけない**。プラグイン側は width/height で描画するため、プラグインで正常に見えても本家 PureRef ではずれていることがある。最終確認は本家 PureRef 実機で行う
