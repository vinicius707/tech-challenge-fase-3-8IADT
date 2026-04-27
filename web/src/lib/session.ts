import { SignJWT, jwtVerify } from "jose";

export const SESSION_COOKIE = "mw_session";

export type SessionPayload = {
  sub: string;
  email: string;
  name: string;
};

export function getAuthSecretKey(): Uint8Array {
  const s = process.env.AUTH_SECRET;
  if (!s || s.length < 32) {
    throw new Error("AUTH_SECRET deve ter pelo menos 32 caracteres.");
  }
  return new TextEncoder().encode(s);
}

export async function signSessionToken(payload: SessionPayload): Promise<string> {
  return await new SignJWT({
    email: payload.email,
    name: payload.name,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(payload.sub)
    .setIssuedAt()
    .setExpirationTime("7d")
    .sign(getAuthSecretKey());
}

export async function verifySessionToken(token: string): Promise<SessionPayload> {
  const { payload } = await jwtVerify(token, getAuthSecretKey(), {
    algorithms: ["HS256"],
  });
  const sub = payload.sub;
  const email = typeof payload.email === "string" ? payload.email : "";
  const name = typeof payload.name === "string" ? payload.name : "";
  if (!sub || !email) throw new Error("Sessão inválida");
  return { sub, email, name };
}

export function sessionCookieOptions(maxAgeSec: number) {
  const secure = process.env.NODE_ENV === "production";
  return {
    httpOnly: true as const,
    sameSite: "lax" as const,
    secure,
    path: "/",
    maxAge: maxAgeSec,
  };
}
