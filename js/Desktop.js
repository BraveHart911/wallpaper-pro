// Screen coordinates are logical pixels supplied by Qt/Wayland, not physical mode pixels.
function bounds(screens) {
    const usable = screens.filter(s => isFinite(s.x) && isFinite(s.y) && s.width > 0 && s.height > 0)
    if (!usable.length) return {left: 0, top: 0, width: 0, height: 0}
    const left = Math.min.apply(null, usable.map(s => s.x))
    const top = Math.min.apply(null, usable.map(s => s.y))
    return {left: left, top: top,
        width: Math.max.apply(null, usable.map(s => s.x + s.width)) - left,
        height: Math.max.apply(null, usable.map(s => s.y + s.height)) - top}
}

function colors(text) {
    const palette = {background: "#111820", foreground: "#f1f5f9", accent: "#7ce2c0", muted: "#a4b4c4", selection: "#1d2935", red: "#ffb4a9"}
    text.split(/\r?\n/).forEach(line => {
        const match = line.match(/^\s*(background|foreground|accent|muted|selection|red)\s*=\s*["'](#[0-9a-fA-F]{6})["']/)
        if (match) palette[match[1]] = match[2]
    })
    return palette
}
