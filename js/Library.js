function ordered(items, order) {
    if (order === "original") return items
    return items.slice().sort(function(a, b) {
        const names = String(a.name || "").toLowerCase().localeCompare(String(b.name || "").toLowerCase()) || String(a.id).localeCompare(String(b.id))
        if (order === "name") return names
        const knownA = !!a.dominantColor, knownB = !!b.dominantColor
        if (knownA !== knownB) return knownA ? -1 : 1
        if (!knownA) return names
        const neutral = Number(!!a.colorNeutral) - Number(!!b.colorNeutral)
        if (neutral) return neutral
        if (a.colorNeutral) return a.colorValue - b.colorValue || names
        return a.colorHue - b.colorHue || a.colorValue - b.colorValue || names
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
