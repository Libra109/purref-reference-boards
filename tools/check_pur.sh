#!/bin/bash
# Check that a .pur file opens in the user's Obsidian plugin (LazyRef PUR Viewer)
# by running the plugin's own parser (parsePur) from Libra109/obsidian-pur-viewer.
# Usage: check_pur.sh <file.pur> [more.pur ...]
cd "$(dirname "$0")/plugin-test" && exec npx tsx harness.mts "$@"
