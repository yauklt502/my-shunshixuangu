import { NextResponse } from "next/server";
import { parseSnapshotQuery, buildSnapshot } from "@/lib/snapshot";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const query = parseSnapshotQuery(url.searchParams);
  try {
    const snapshot = await buildSnapshot(query);
    return NextResponse.json(snapshot, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "行情获取失败";
    return NextResponse.json(
      {
        tradeDate: "",
        updatedAt: new Date().toISOString(),
        session: "closed",
        universe: query.universe,
        sort: query.sort,
        indices: [],
        ztCount: 0,
        zbCount: 0,
        sectors: [],
        error: message,
      },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}
