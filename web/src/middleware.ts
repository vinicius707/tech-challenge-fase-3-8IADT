import { NextResponse, type NextRequest } from "next/server";
import { jwtVerify } from "jose";
import { getAuthSecretKey, SESSION_COOKIE } from "@/lib/session";

function redirectLogin(req: NextRequest) {
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("from", req.nextUrl.pathname + req.nextUrl.search);
  return NextResponse.redirect(url);
}

export async function middleware(req: NextRequest) {
  const token = req.cookies.get(SESSION_COOKIE)?.value;
  if (!token) return redirectLogin(req);
  try {
    await jwtVerify(token, getAuthSecretKey(), { algorithms: ["HS256"] });
    return NextResponse.next();
  } catch {
    return redirectLogin(req);
  }
}

export const config = {
  matcher: ["/atendimentos/:path*", "/api/atendimentos/:path*", "/api/chat/stream"],
};
