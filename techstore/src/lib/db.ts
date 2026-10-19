import { DatabaseSync } from "node:sqlite";
import { resolve } from "node:path";

let dbInstance: DatabaseSync | null = null;

export function getDb(): DatabaseSync {
  if (!dbInstance) {
    const dbPath = resolve(process.cwd(), "data/techstore.db");
    dbInstance = new DatabaseSync(dbPath);
  }
  return dbInstance;
}

export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
}

export interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
  stock: number;
  rating: number;
  description: string;
}

export interface Coupon {
  code: string;
  discount_percent: number;
  is_active: number;
  min_order_usd: number;
  expiry_date: string;
}

export interface Order {
  id: string;
  user_email: string;
  items: string;
  subtotal: number;
  discount: number;
  shipping: number;
  total: number;
  status: string;
  created_at: string;
}
