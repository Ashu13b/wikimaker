export function normalizeUrl(url: string): string {
  let normalized = (url || "").trim().toLowerCase();
  if (normalized.startsWith("https://")) normalized = normalized.slice(8);
  else if (normalized.startsWith("http://")) normalized = normalized.slice(7);
  if (normalized.startsWith("www.")) normalized = normalized.slice(4);
  if (normalized.includes("#")) normalized = normalized.split("#")[0];
  if (normalized.includes("?")) normalized = normalized.split("?")[0];
  if (normalized.endsWith("/")) normalized = normalized.slice(0, -1);
  return normalized;
}

export function getHostname(url: string): string {
  if (!url) return "";
  try {
    const u = url.startsWith("http") ? url : `https://${url}`;
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function safeHref(url: string | null | undefined): string {
  if (!url) return "#";
  const trimmed = url.trim();
  const lower = trimmed.toLowerCase();
  if (lower.startsWith("javascript:") || lower.startsWith("vbscript:") || lower.startsWith("data:")) {
    return "#";
  }
  if (!lower.startsWith("http://") && !lower.startsWith("https://") && !lower.startsWith("mailto:") && !lower.startsWith("#") && !lower.startsWith("/")) {
    return `https://${trimmed}`;
  }
  return trimmed;
}
