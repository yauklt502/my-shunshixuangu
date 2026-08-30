"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-[70vh] max-w-lg flex-col items-start justify-center gap-4 px-6">
      <p className="text-xs tracking-[0.22em] text-gold">SHUNSHI XUANGU</p>
      <h1 className="text-2xl font-semibold">页面没有加载出来</h1>
      <p className="text-sm leading-6 text-muted">
        {error.message || "服务暂时不可用。本地请用 npm run dev；如果是 Cloudflare 部署失败，需要带上 Workers 适配配置后再发一版。"}
      </p>
      <button
        type="button"
        onClick={reset}
        className="rounded-full bg-gold px-4 py-2 text-sm font-medium text-black"
      >
        重试
      </button>
    </main>
  );
}
