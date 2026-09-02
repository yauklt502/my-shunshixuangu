export type Host = "his" | "hq" | "shhq" | "lhb";

export class ApiError extends Error {
  errcode: string;
  constructor(message: string, errcode = "1") {
    super(message);
    this.errcode = errcode;
  }
}

export type CommonParams = {
  DeviceID: string;
  PhoneOSNew: string;
  VerSion: string;
  apiv: string;
  Token?: string;
  UserID?: string;
};

export async function kpl<T = Record<string, unknown>>(opts: {
  host: Host;
  method?: "GET" | "POST";
  params: Record<string, string | number | undefined>;
  common: CommonParams;
}): Promise<T> {
  const response = await fetch("/api/kpl", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(opts),
  });
  const data = (await response.json()) as T & { errcode?: string | number; errmsg?: string };
  if (!response.ok) {
    throw new ApiError(data.errmsg || `请求失败 HTTP ${response.status}`, String(data.errcode ?? response.status));
  }
  if (data.errcode !== undefined && String(data.errcode) !== "0") {
    throw new ApiError(data.errmsg || `接口错误 ${data.errcode}`, String(data.errcode));
  }
  return data;
}

export function liveHost(date: string, today: string): Host {
  return date === today ? "hq" : "his";
}
