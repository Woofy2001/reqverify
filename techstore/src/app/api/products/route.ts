import { NextResponse } from "next/server";
import { getDb, Product } from "@/lib/db";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const category = searchParams.get("category");
    const maxPrice = searchParams.get("maxPrice");

    const db = getDb();
    let query = "SELECT * FROM products WHERE 1=1";
    const params: any[] = [];

    if (category && category !== "All") {
      query += " AND category = ?";
      params.push(category);
    }

    if (maxPrice) {
      query += " AND price <= ?";
      params.push(parseFloat(maxPrice));
    }

    query += " ORDER BY price ASC";
    const stmt = db.prepare(query);
    const products = stmt.all(...params) as unknown as Product[];

    return NextResponse.json({ products });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
