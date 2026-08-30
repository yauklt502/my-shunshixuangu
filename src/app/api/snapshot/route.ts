import { NextResponse } from "next/server";
import { parseSnapshotQuery, buildSnapshot } from "@/lib/snapshot";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

function emptySnapshot(query: ReturnType<typeof parseSnapshotQuery>, error: string) {
  return {
    tradeDate: "",
    updatedAt: new Date().toISOString(),
    session: "closed" as const,
    universe: query.universe,
    sort: query.sort,
    source: query.source,
    indices: [],
    ztCount: 0,
    zbCount: 0,
    sectors: [],
    error,
  };
}

function readFuyaoKey(request: Request): string {
  return (
    request.headers.get("x-fuyao-key") ||
    request.headers.get("x-api-key") ||
    process.env.FUYAO_API_KEY ||
    ""
  ).trim();
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const query = parseSnapshotQuery(url.searchParams);
  try {
    const snapshot = await buildSnapshot(query, {
      fuyaoKey: readFuyaoKey(request),
      tdxVipdoc: url.searchParams.get("vipdoc") || process.env.TDX_VIPDOC || "",
    });
    return NextResponse.json(snapshot, {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "行情暂时不可用";
    return NextResponse.json(emptySnapshot(query, message), {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    });
  }
}
