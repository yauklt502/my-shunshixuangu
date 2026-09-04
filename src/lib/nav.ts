export function openTheme(id?: string) {
  window.location.hash = id ? `/theme/${id}` : "/theme";
}

export function themeIdFromHash(): string {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [page, id] = raw.split("/");
  return page === "theme" && id ? id : "";
}
