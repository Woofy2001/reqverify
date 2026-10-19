import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function POST(req: Request) {
  try {
    const { email, password } = await req.json();
    if (!email || !password) {
      return NextResponse.json({ error: "Email and password are required." }, { status: 400 });
    }

    const db = getDb();
    const stmt = db.prepare("SELECT id, email, role FROM users WHERE email = ? AND password = ?");
    const user = stmt.get(email.trim().toLowerCase(), password) as any;

    if (!user) {
      return NextResponse.json({ error: "Invalid email or password." }, { status: 401 });
    }

    const response = NextResponse.json({
      success: true,
      user: { id: user.id, email: user.email, role: user.role }
    });

    // Set cookie for session
    response.cookies.set("techstore_user", JSON.stringify({ email: user.email, role: user.role }), {
      httpOnly: false, // readable for testing checks
      path: "/",
      maxAge: 86400
    });

    return response;
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
