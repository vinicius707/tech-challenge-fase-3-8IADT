import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

export async function GET() {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ user: null }, { status: 401 });
  try {
    const session = await verifySessionToken(token);
    return NextResponse.json({
      user: { id: session.sub, email: session.email, name: session.name },
    });
  } catch {
    return NextResponse.json({ user: null }, { status: 401 });
  }
}
