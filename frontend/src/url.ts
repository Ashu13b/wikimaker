export function normalizeUrl(url: string): string {
  let normalized = url.trim().toLowerCase();
  if (normalized.startsWith("https://")) normalized = normalized.slice(8);
  else if (normalized.startsWith("http://")) normalized = normalized.slice(7);
  if (normalized.startsWith("www.")) normalized = normalized.slice(4);
  if (normalized.includes("#")) normalized = normalized.split("#")[0];
  if (normalized.includes("?")) normalized = normalized.split("?")[0];
  if (normalized.endsWith("/")) normalized = normalized.slice(0, -1);
  return normalized;
}
