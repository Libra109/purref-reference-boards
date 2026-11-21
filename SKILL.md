# PureRef reference boards as .pur files

## Generate the board in 2.x format

- Build the reference set as a PureRef .pur file instead of handing over images one by one when the user asks for a reference set.

- Generate the file with the Python generator at `tools/gen_pur.py` (with `tools/purcore.py` and `tools/template_data.py` next to it): `python3 tools/gen_pur.py <PNG folder> <output.pur>`. It needs Python 3.10+ and the standard library only — no Rust, no build step, no template .pur at runtime.

- Put only PNG files in the input folder.

- Convert any JPG or other non-PNG source to PNG before you run the generator, because the generator keeps only files with a png extension and silently leaves out every other file.

- The generator embeds each PNG file's bytes as they are and records the format as PNG.

- Expect a single row in filename order with a 20 pixel gap between images, because that is the layout the generator builds.

- The generator verifies its own output by reading it back with the container checksum checked, and prints the image count and sizes; treat a failed self-check as a failed generation.

- Do not use an old-format (1.x) generator for a file meant for the plugin parser, because it writes the old format and that parser accepts container 2.1 only.

- The Rust generator at `tools/gen2x.rs` (a LazyRef purcore example) is kept as the reference implementation the Python port was verified against — byte-identical output on real boards. Use it only when you specifically need the Rust form; it needs a LazyRef checkout, a Rust build, and the fixture `crates/purcore/tests/fixtures/S1_redbar-new.pur` as its template argument. Never pass a material board as that template, because the frames get scaled twice and PureRef shows the images oversized.

## Verify the file in the plugin parser

- Run `tools/check_pur.sh <file.pur>` on every file before you hand it over (setup for the parser environment is in SETUP.md).

- Read the parser result for the file version and the image count and sizes and any warnings.

- Compare the parser image count with the PNG files you put in, because a file the generator left out shows up only as a missing image.

- Hand over a file only when the parser opens it with zero warnings.

- Report the image count and sizes and the zero warning result with the file so the user can see the check happened.

- Say plainly that opening in genuine PureRef is still unconfirmed when you have not tested it there.

## Present the result

- Name the images in the board and the layout you used when you hand the file over.

- Keep the source image list with the output file so a later mismatch can be traced to one image.

## Available connectors

- Search pixiv for reference illustrations with the pixiv App API connector, when one is set up.

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with the Custom Connectors and MCPs skill, or build a custom connector.

## Alternatives for better results

- Ask the user which images belong in the board and how they should be grouped before you generate a large board.

- Offer a smaller test board first when the image set is large so the generation and parser check can be proven on a few images.
