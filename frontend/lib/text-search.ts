export function normalizeSearchText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR")
    .trim();
}

function editDistance(left: string, right: string): number {
  const previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let row = 1; row <= left.length; row += 1) {
    let diagonal = previous[0];
    previous[0] = row;
    for (let column = 1; column <= right.length; column += 1) {
      const above = previous[column];
      previous[column] = Math.min(
        previous[column] + 1,
        previous[column - 1] + 1,
        diagonal + (left[row - 1] === right[column - 1] ? 0 : 1),
      );
      diagonal = above;
    }
  }
  return previous[right.length];
}

export function suggestSimilarText(query: string, values: string[], limit = 3): string[] {
  const term = normalizeSearchText(query);
  const queryWords = term.split(/\s+/).filter(Boolean);
  if (!term || queryWords.some(word => word.length < 3)) return [];
  return [...new Set(values)]
    .map((value) => {
      const words = normalizeSearchText(value).split(/\s+/).filter(Boolean);
      const thresholds = queryWords.map((queryWord) => queryWord.length >= 8 ? 2 : 1);
      const distances = queryWords.map((queryWord) =>
        Math.min(...words.map((word) => editDistance(queryWord, word))),
      );
      return {
        value,
        distance: distances.reduce((sum, distance) => sum + distance, 0),
        typoCount: distances.filter((distance) => distance > 0).length,
        withinThreshold: distances.every((distance, index) => distance <= thresholds[index]),
        maxDistance: queryWords.length >= 3
          ? 2
          : thresholds.reduce((sum, threshold) => sum + threshold, 0),
      };
    })
    .filter((item) => item.typoCount > 0 && item.withinThreshold && item.distance <= item.maxDistance)
    .sort((left, right) =>
      left.distance - right.distance || left.value.localeCompare(right.value, "pt-BR"),
    )
    .slice(0, limit)
    .map((item) => item.value);
}
