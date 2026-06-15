import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const headers = new Headers(request.headers);
  headers.set("X-Internal-Token", process.env.BACKEND_INTERNAL_TOKEN ?? "development-internal-token");
  headers.set("X-Workspace-ID", process.env.WORKSPACE_ID ?? "demo-workspace");
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: "/api/:path*" };

