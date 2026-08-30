declare global {
  interface Window {
    html2canvas?: (
      element: HTMLElement,
      options?: Record<string, unknown>,
    ) => Promise<HTMLCanvasElement>;
  }
}

const HTML2CANVAS_SRC = "https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js";

function loadHtml2Canvas(): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("browser only"));
  if (window.html2canvas) return Promise.resolve();
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${HTML2CANVAS_SRC}"]`)) {
      resolve();
      return;
    }
    const tag = document.createElement("script");
    tag.src = HTML2CANVAS_SRC;
    tag.onload = () => resolve();
    tag.onerror = () => reject(new Error("截屏组件加载失败，请检查网络"));
    document.head.appendChild(tag);
  });
}

function downloadDataUrl(dataUrl: string, filename: string) {
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export function beijingStamp(date = new Date()): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Shanghai",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  })
    .format(date)
    .replaceAll(":", "");
}

export type SaveScreenshotResult =
  | { ok: true; path?: string; filename: string; downloaded: boolean }
  | { ok: false; error: string };

export async function savePageScreenshot(
  target: HTMLElement,
  filename: string,
): Promise<SaveScreenshotResult> {
  await loadHtml2Canvas();
  const html2canvas = window.html2canvas;
  if (!html2canvas) throw new Error("截屏组件未就绪");

  const canvas = await html2canvas(target, {
    backgroundColor: "#07080c",
    scale: Math.min(2, window.devicePixelRatio || 1),
    useCORS: true,
    allowTaint: true,
    logging: false,
  });
  const dataUrl = canvas.toDataURL("image/png");

  try {
    const res = await fetch("/save-screenshot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, data: dataUrl }),
    });
    const result = (await res.json()) as { ok?: boolean; path?: string; error?: string };
    if (result.ok) {
      downloadDataUrl(dataUrl, filename);
      return { ok: true, path: result.path, filename, downloaded: true };
    }
    throw new Error(result.error || "本地保存失败");
  } catch (error) {
    downloadDataUrl(dataUrl, filename);
    const message = error instanceof Error ? error.message : "本地保存失败";
    return { ok: false, error: message };
  }
}
