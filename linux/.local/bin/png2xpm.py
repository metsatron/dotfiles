#!/usr/bin/env python3
"""Convert a PNG to XPM (with transparency mask) for xclass/libXpm.
Usage: png2xpm.py input.png output.xpm [name]
Builds a palette; cpp=1 if <=94 colours else cpp=2. Transparent pixels -> None.
"""
import sys, os
from PIL import Image

def png_to_xpm(src, dst, name=None):
    im = Image.open(src)
    if im.mode not in ("RGBA", "RGB"):
        im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    palette = []
    palidx = {}
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b, a = px[x, y]
            key = None if a < 128 else (r, g, b)
            if key not in palidx:
                palidx[key] = len(palette)
                palette.append(key)
            row.append(palidx[key])
        rows.append(row)
    ncol = len(palette)
    # Safe single-char alphabet: printable ASCII 33..126 EXCLUDING the XPM
    # string delimiter (0x22) and backslash (0x5c). Using the quote char as a
    # pixel corrupts the XPM; XpmReadFileToPixmap then fails -> generic icons.
    _SAFE1 = [chr(c) for c in range(33, 127) if c not in (0x22, 0x5c)]
    if ncol <= len(_SAFE1):
        cpp = 1
        chars = _SAFE1[:ncol]
    else:
        cpp = 2
        chars = []
        for c1 in range(33, 127):
            if c1 in (0x22, 0x5c): continue
            for c2 in range(33, 127):
                if c2 in (0x22, 0x5c): continue
                chars.append(chr(c1) + chr(c2))
                if len(chars) >= ncol: break
            if len(chars) >= ncol: break
    if not name:
        name = os.path.splitext(os.path.basename(dst))[0]
        name = "".join(c if c.isalnum() else "_" for c in name)
    lines = ["/* XPM */",
             "static char * %s[] = {" % name,
             '"%d %d %d %d",' % (w, h, ncol, cpp)]
    for i, key in enumerate(palette):
        if key is None:
            lines.append('"%s c None",' % chars[i])
        else:
            lines.append('"%s c #%02X%02X%02X",' % (chars[i], key[0], key[1], key[2]))
    for y in range(h):
        s = "".join(chars[rows[y][x]] for x in range(w))
        sep = "}" if y == h - 1 else ","
        lines.append('"%s"%s' % (s, sep))
    lines.append("};")
    with open(dst, "w") as f:
        f.write("\n".join(lines) + "\n")
    return (w, h, ncol)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: png2xpm.py input.png output.xpm [name]")
    w, h, n = png_to_xpm(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print("%s -> %s (%dx%d, %d colours)" % (sys.argv[1], sys.argv[2], w, h, n))
