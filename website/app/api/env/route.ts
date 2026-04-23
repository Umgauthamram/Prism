import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_ENV_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const path = request.nextUrl.pathname.replace("/api/env", "");
  const query = searchParams.toString();
  
  const targetUrl = `${BACKEND_URL}${path}${query ? `?${query}` : ""}`;
  
  try {
    const res = await fetch(targetUrl);
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 });
  }
}

export async function POST(request: NextRequest) {
  const path = request.nextUrl.pathname.replace("/api/env", "");
  const body = await request.json();
  
  const targetUrl = `${BACKEND_URL}${path}`;
  
  try {
    const res = await fetch(targetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 });
  }
}
