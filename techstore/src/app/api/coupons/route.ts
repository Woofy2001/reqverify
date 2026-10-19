import { NextResponse } from "next/server";
import { getDb, Coupon } from "@/lib/db";

export async function POST(req: Request) {
  try {
    const { code } = await req.json();
    if (!code) {
      return NextResponse.json({ valid: false, error: "Coupon code is required." }, { status: 400 });
    }

    const db = getDb();
    const stmt = db.prepare("SELECT * FROM coupons WHERE code = ?");
    const coupon = stmt.get(code.trim().toUpperCase()) as Coupon | undefined;

    if (!coupon) {
      return NextResponse.json({ valid: false, error: "Invalid coupon code." }, { status: 404 });
    }

    const today = new Date().toISOString().split("T")[0];
    if (coupon.is_active !== 1 || coupon.expiry_date < today) {
      return NextResponse.json({ valid: false, error: "This coupon code has expired." }, { status: 400 });
    }

    return NextResponse.json({
      valid: true,
      code: coupon.code,
      discount_percent: coupon.discount_percent,
      message: `${coupon.discount_percent}% discount applied successfully!`
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
