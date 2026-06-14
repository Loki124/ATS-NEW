# Fonts Directory

This directory is reserved for bundled font assets.

Currently empty by design: the PDF generator (Todo #6) loads CJK fonts from
the system at runtime, using `cjk-font-loader.js` to discover common paths:

- macOS: `/System/Library/Fonts/Hiragino Sans GB.ttc`, `STHeiti Medium.ttc`
- Linux: `/usr/share/fonts/truetype/wqy/wqy-microhei.ttc`, Noto CJK
- Windows: `C:\Windows\Fonts\msyh.ttc`

If you need to ship a font with the project (e.g., for minimal containers
without system CJK fonts), drop a `.ttf` or `.otf` here and add its path
to `CJK_FONT_PATHS` in `services/cjk-font-loader.js`.
