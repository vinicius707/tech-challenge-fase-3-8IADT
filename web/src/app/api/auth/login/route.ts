import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { getDb, runMigrations } from "@/db/client";
import {
  SESSION_COOKIE,
  sessionCookieOptions,
  signSessionToken,
} from "@/lib/session";

export const runtime = "nodejs";

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "JSON inválido" }, { status: 400 });
  }
  const email = typeof (body as { email?: unknown })?.email === "string"
    ? String((body as { email: string }).email).trim().toLowerCase()
    : "";
  const password =
    typeof (body as { password?: unknown })?.password === "string"
      ? String((body as { password: string }).password)
      : "";
  if (!email || !password) {
    return NextResponse.json({ error: "Credenciais em falta" }, { status: 400 });
  }

  try {
    runMigrations();
    const db = getDb();
    const row = db
      .prepare(
        `SELECT id, email, name, password_hash FROM users WHERE email = ? LIMIT 1`,
      )
      .get(email) as
      | { id: string; email: string; name: string; password_hash: string }
      | undefined;

    const ok = row && bcrypt.compareSync(password, row.password_hash);
    if (!ok) {
      return NextResponse.json({ error: "Email ou palavra-passe inválidos." }, { status: 401 });
    }

    const token = await signSessionToken({
      sub: row!.id,
      email: row!.email,
      name: row!.name,
    });

    const res = NextResponse.json({ ok: true, user: { id: row!.id, email: row!.email, name: row!.name } });
    res.cookies.set(SESSION_COOKIE, token, sessionCookieOptions(60 * 60 * 24 * 7));
    return res;
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Erro interno";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
