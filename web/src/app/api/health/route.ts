import { NextResponse } from "next/server";

export function GET() {
  const mode = process.env.ORCHESTRATION_API_URL ? "proxy" : "stub";
  return NextResponse.json({ ok: true, mode });
}
