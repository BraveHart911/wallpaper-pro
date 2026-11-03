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
