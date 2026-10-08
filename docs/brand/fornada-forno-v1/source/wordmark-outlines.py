"""Export the chosen installed font as outlines; never redistribute the font file."""
import json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen

font = TTFont(r"C:\Windows\Fonts\seguisb.ttf")
glyphs = font.getGlyphSet()
cmap = font.getBestCmap()
paths = []
x = 0
bounds = BoundsPen(glyphs)
for char in "fornada":
    glyph = glyphs[cmap[ord(char)]]
    pen = SVGPathPen(glyphs)
    glyph.draw(TransformPen(pen, (1, 0, 0, 1, x, 0)))
    glyph.draw(TransformPen(bounds, (1, 0, 0, 1, x, 0)))
    paths.append(pen.getCommands())
    x += glyph.width - 32

result = {"text":"fornada", "font":"Segoe UI Semibold", "unitsPerEm":font["head"].unitsPerEm, "bounds":bounds.bounds, "paths":paths}
Path(__file__).with_name("wordmark-outlines.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(result["font"], result["unitsPerEm"], result["bounds"])
