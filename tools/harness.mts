import { readFileSync } from "node:fs";
import { parsePur } from "./parser";

for (const path of process.argv.slice(2)) {
  console.log("=== " + path);
  try {
    const board = await parsePur(new Uint8Array(readFileSync(path)));
    console.log("version:", board.version);
    console.log("images:", board.images.length);
    for (const im of board.images) {
      console.log(`  id=${im.id} ${im.width}x${im.height} mime=${im.mime} dataBytes=${im.data?.length} item=${JSON.stringify(im.item)} z=${im.z}`);
    }
    console.log("warnings:", JSON.stringify(board.warnings));
    if (board.structureIssue) console.log("structureIssue:", board.structureIssue);
  } catch (e) {
    console.log("ERROR:", (e as Error).message);
  }
}
