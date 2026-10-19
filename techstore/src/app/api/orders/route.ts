import { NextResponse } from "next/server";
import { getDb, Order } from "@/lib/db";

export async function GET() {
  try {
    const db = getDb();
    const stmt = db.prepare("SELECT * FROM orders ORDER BY created_at DESC");
    const orders = stmt.all() as unknown as Order[];
    return NextResponse.json({ orders });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { user_email, items, subtotal, discount, shipping, total } = body;

    if (!user_email || !items || subtotal === undefined) {
      return NextResponse.json({ error: "Missing required order fields." }, { status: 400 });
    }

    const db = getDb();
    const orderId = `ORD-${Date.now().toString().slice(-4)}`;
    const createdAt = new Date().toISOString();

    const stmt = db.prepare(`
      INSERT INTO orders (id, user_email, items, subtotal, discount, shipping, total, status, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
    `);

    stmt.run(
      orderId,
      user_email,
      typeof items === "string" ? items : JSON.stringify(items),
      subtotal,
      discount || 0,
      shipping || 15.00,
      total,
      createdAt
    );

    return NextResponse.json({
      success: true,
      order_id: orderId,
      status: "Pending",
      message: "Order placed successfully!"
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function PATCH(req: Request) {
  try {
    const { order_id, status } = await req.json();
    if (!order_id || !status) {
      return NextResponse.json({ error: "order_id and status are required." }, { status: 400 });
    }

    const db = getDb();
    const stmt = db.prepare("UPDATE orders SET status = ? WHERE id = ?");
    const info = stmt.run(status, order_id);

    if (info.changes === 0) {
      return NextResponse.json({ error: "Order not found." }, { status: 404 });
    }

    return NextResponse.json({ success: true, order_id, status });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
