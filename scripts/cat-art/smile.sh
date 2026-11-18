#!/usr/bin/env sh
# Make the font of the ":3" the footer cat gives back when it is pressed, src/assets/cat/smile.woff.
#
# It is Caveat (SIL Open Font License), cut down to the two characters of ":3", so that it is
# about 1 KB and not 48.
#
# WOFF and not WOFF2: fontTools needs brotli for WOFF2, and at this size there is little to gain.
# Needs npm and fontTools (pyftsubset).
set -e
cd "$(dirname "$0")"
out="$(pwd)/../../src/assets/cat/smile.woff"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
(cd "$work" && npm pack @fontsource/caveat --silent >/dev/null && tar xzf fontsource-caveat-*.tgz)
pyftsubset "$work/package/files/caveat-latin-400-normal.woff" \
    --text=":3" --layout-features='*' --flavor=woff --output-file="$out"
