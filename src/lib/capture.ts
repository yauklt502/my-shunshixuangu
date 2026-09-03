import html2canvas from "html2canvas";

export async function downloadPagePng(filename: string, root: HTMLElement = document.body) {
  const canvas = await html2canvas(root, {
    backgroundColor: "#ffffff",
    scale: Math.min(2, window.devicePixelRatio || 2),
    useCORS: true,
    logging: false,
  });
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("截屏失败");
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1500);
}