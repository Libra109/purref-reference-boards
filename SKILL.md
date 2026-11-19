# PureRef reference boards as .pur files

## Generate the board in 2.x format

- Build the reference set as a PureRef .pur file instead of handing over images one by one when the user asks for a reference set.

- Generate the file with the LazyRef purcore 2.x generator at `~/workspace/pureref-lab/LazyRef/crates/purcore/examples/gen2x.rs`.

- Put only PNG files in the input folder.

- Convert any JPG or other non-PNG source to PNG before you run the generator, because the generator keeps only files with a png extension and silently leaves out every other file.

- The generator embeds each PNG file's bytes as they are and records the format as PNG.

- Expect a single row in filename order with a 20 pixel gap between images, because that is the layout the generator builds.

- Do not use the old-format generator at `~/workspace/pureref-lab/PureRef-format/pureref_gen.py` for a file meant for the plugin parser, because it writes the old format and that parser accepts container 2.1 only.

## Verify the file in the plugin parser

- Run `~/workspace/pureref-lab/check_pur.sh <file.pur>` on every file before you hand it over.

- Read the parser result for the file version and the image count and sizes and any warnings.

- Compare the parser image count with the PNG files you put in, because a file the generator left out shows up only as a missing image.

- Hand over a file only when the parser opens it with zero warnings.

- Report the image count and sizes and the zero warning result with the file so the user can see the check happened.

- Say plainly that opening in genuine PureRef is still unconfirmed when you have not tested it there.

## Present the result

- Name the images in the board and the layout you used when you hand the file over.

- Keep the source image list with the output file so a later mismatch can be traced to one image.

## Available connectors

- Search pixiv for reference illustrations with [pixiv App API](~/workspace/custom-connectors/custom.pixiv/CONNECTOR.md).

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Ask the user which images belong in the board and how they should be grouped before you generate a large board.

- Offer a smaller test board first when the image set is large so the generation and parser check can be proven on a few images.
