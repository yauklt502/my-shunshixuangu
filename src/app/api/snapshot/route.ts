import { NextResponse } from "next/server";
import { parseSnapshotQuery, buildSnapshot } from "@/lib/snapshot";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

function emptySnapshot(universe: ReturnType<typeof parseSnapshotQuery>["universe"], sort: ReturnType<typeof parseSnapshotQuery>["sort"], error: string) {
  return {
    tradeDate: "",
    updatedAt: new Date().toISOString(),
    session: "closed" as const,
    universe,
    sort,
    indices: [],
    ztCount: 0,
    zbCount: 0,
    sectors: [],
    error,
  };
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const query = parseSnapshotQuery(url.searchParams);
  try {
    const snapshot = await buildSnapshot(query);
    return NextResponse.json(snapshot, {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "行情暂时不可用";
    return NextResponse.json(emptySnapshot(query.universe, query.sort, message), {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    });
  }
}
