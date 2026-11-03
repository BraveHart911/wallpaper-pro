function colorBand(item) {
    if (!item.dominantColor) return 15
    if (item.colorNeutral) return 12 + (item.colorValue < 0.22 ? 0 : item.colorValue > 0.78 ? 2 : 1)
    return Math.floor(((item.colorHue + 15) % 360) / 30)
}

function compareNames(a, b) {
    return String(a.name || "").toLowerCase().localeCompare(String(b.name || "").toLowerCase()) || String(a.id).localeCompare(String(b.id))
}

function ordered(items, order, smart) {
    if (order === "original") return items
    const contextual = smart === true && items.some(item => !!item.contextGroup)
    return items.slice().sort(function(a, b) {
        if (order === "name") return compareNames(a, b)
        const knownA = !!a.dominantColor, knownB = !!b.dominantColor
        if (knownA !== knownB) return knownA ? -1 : 1
        if (!knownA) return compareNames(a, b)
        if (contextual) {
            const band = colorBand(a) - colorBand(b)
            if (band) return band
            const group = (a.contextGroup || "~Unclassified").localeCompare(b.contextGroup || "~Unclassified")
            if (group) return group
            if (a.contextGroup && b.contextGroup) {
                const rank = (a.contextRank || 0) - (b.contextRank || 0)
                if (rank) return rank
            }
        }
        const neutral = Number(!!a.colorNeutral) - Number(!!b.colorNeutral)
        if (neutral) return neutral
        if (a.colorNeutral) return a.colorValue - b.colorValue || compareNames(a, b)
        return a.colorHue - b.colorHue || a.colorValue - b.colorValue || compareNames(a, b)
    })
}

function spectrumIndex(count, fraction) {
    if (count <= 0) return -1
    return Math.round(Math.max(0, Math.min(1, fraction)) * (count - 1))
}

function spectrumStops(items, limit) {
    if (!items.length) return [{position: 0, color: "#777777"}, {position: 1, color: "#777777"}]
    const count = Math.max(2, Math.min(limit || 96, items.length))
    const stops = []
    for (let i = 0; i < count; i++) {
        const fraction = i / (count - 1)
        const index = spectrumIndex(items.length, fraction)
        stops.push({position: fraction, color: items[index].dominantColor || "#777777"})
    }
    return stops
}
