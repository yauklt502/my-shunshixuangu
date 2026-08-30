import { NextResponse } from "next/server";
import { buildLT88Snapshot, parseLT88Query } from "@/lib/longtou88/snapshot";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(request: Request) {
  const url = new URL(request.url);
  const query = parseLT88Query(url.searchParams);
  try {
    const snapshot = await buildLT88Snapshot(query);
    return NextResponse.json(snapshot, {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "行情暂时不可用";
    return NextResponse.json(
      {
        tradeDate: query.date,
        updatedAt: new Date().toISOString(),
        session: "closed" as const,
        universe: query.universe,
        sort: query.sort,
        source: query.source,
        indices: [],
        ztCount: 0,
        zbCount: 0,
        sectors: [],
        error: message,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  }
}
