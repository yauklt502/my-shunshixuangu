const NOISE_PATTERNS: RegExp[] = [
  /昨日/,
  /前日/,
  /连板/,
  /涨停/,
  /跌停/,
  /破板/,
  /炸板/,
  /打板/,
  /打二板/,
  /首板/,
  /二板/,
  /三板/,
  /历史新高/,
  /历史新低/,
  /近期新高/,
  /近期新低/,
  /近期解禁/,
  /公告/,
  /^ST/,
  /ST股/,
  /ST板块/,
  /次新股/,
  /次新债/,
  /沪股通/,
  /深股通/,
  /融资融券/,
  /转融通/,
  /高开低走/,
  /低开高走/,
  /高换手/,
  /成交活跃/,
  /含一字/,
  /题材股/,
  /热股/,
  /多板/,
  /东方财富/,
];

export function isNoiseBoard(name: string): boolean {
  const trimmed = name.trim();
  return NOISE_PATTERNS.some((pattern) => pattern.test(trimmed));
}

export function isStStock(name: string): boolean {
  return /(?:\*?ST|S\*ST|\bST)/i.test(name.replaceAll(" ", ""));
}
