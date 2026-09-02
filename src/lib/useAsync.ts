import { useCallback, useEffect, useRef, useState } from "react";

export function useAsync<T>(factory: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const seq = useRef(0);

  const reload = useCallback(() => {
    const id = ++seq.current;
    setLoading(true);
    factory()
      .then((result) => {
        if (id !== seq.current) return;
        setData(result);
        setError(null);
      })
      .catch((err: Error) => {
        if (id !== seq.current) return;
        setError(err.message || "加载失败");
      })
      .finally(() => {
        if (id !== seq.current) return;
        setLoading(false);
      });
    // factory identity is controlled by deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload, setData };
}
