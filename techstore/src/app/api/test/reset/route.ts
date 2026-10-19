import { NextResponse } from "next/server";
import { execSync } from "node:child_process";
import { resolve } from "node:path";

export async function POST() {
  try {
    const seedScript = resolve(process.cwd(), "scripts/seed.mjs");
    execSync(`node "${seedScript}"`, { stdio: "inherit" });
    return NextResponse.json({ success: true, message: "TechStore database reset to initial seed state." });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
