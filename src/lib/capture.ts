import html2canvas from "html2canvas";

export async function downloadPagePng(filename: string, root: HTMLElement = document.body) {
  const canvas = await html2canvas(root, {
    backgroundColor: "#ffffff",
    scale: Math.min(2, window.devicePixelRatio || 2),
    useCORS: true,
    logging: false,
    onclone: (_doc, cloned) => {
      cloned.style.background = "#ffffff";
      cloned.querySelectorAll<HTMLElement>(".topbar").forEach((bar) => {
        bar.style.background = "#ffffff";
        bar.style.backdropFilter = "none";
      });
    },
  });
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("截屏失败");
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1500);
}