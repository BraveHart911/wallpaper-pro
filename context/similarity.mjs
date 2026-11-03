export const normalize = vector => {
 const length = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0)) || 1;
 return vector.map(value => value / length);
};
export const dot = (a, b) => {
 let value = 0;
 for (let i = 0; i < a.length; i++) value += a[i] * b[i];
 return value;
};
export function band(item) {
 if (!item.dominantColor) return 15;
 if (item.colorNeutral) return 12 + (item.colorValue < .22 ? 0 : item.colorValue > .78 ? 2 : 1);
 return Math.floor(((item.colorHue + 15) % 360) / 30);
}

export function assignVisualRanks(records, entries) {
const groups = new Map();
for (const record of records) {
 const entry = entries[record.path];
 if (!entry) continue;
 const key = band(record) + ':' + entry.group;
 if (!groups.has(key)) groups.set(key, []);
 groups.get(key).push({record, entry});
}
for (const members of groups.values()) {
 const center = normalize(members[0].entry.embedding.map((_, i) => members.reduce((sum, m) => sum + m.entry.embedding[i],0)/members.length));
 members.sort((a,b) => dot(b.entry.embedding,center)-dot(a.entry.embedding,center) || a.record.id.localeCompare(b.record.id));
 let current = members.shift(), rank = 0;
 while (current) {
  current.entry.rank = rank++;
  if (!members.length) break;
  let best = 0, cost = Infinity;
  for (let i=0; i<members.length; i++) {
   const candidate = members[i];
   const distance = 1-dot(current.entry.embedding,candidate.entry.embedding)
      + .12*Math.abs((current.record.colorHue||0)-(candidate.record.colorHue||0))/30
      + .08*Math.abs((current.record.colorValue||0)-(candidate.record.colorValue||0));
   if (distance < cost) {cost=distance;best=i;}
  }
  current = members.splice(best,1)[0];
 }
}
}
