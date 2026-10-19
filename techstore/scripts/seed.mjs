import { DatabaseSync } from "node:sqlite";
import { mkdirSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dbDir = resolve(__dirname, "../data");
if (!existsSync(dbDir)) {
  mkdirSync(dbDir, { recursive: true });
}

const dbPath = resolve(dbDir, "techstore.db");
const db = new DatabaseSync(dbPath);

console.log("Seeding TechStore deterministic database at:", dbPath);

// Create Schema
db.exec(`
  DROP TABLE IF EXISTS orders;
  DROP TABLE IF EXISTS coupons;
  DROP TABLE IF EXISTS products;
  DROP TABLE IF EXISTS users;

  CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
  );

  CREATE TABLE products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL,
    rating REAL NOT NULL,
    description TEXT NOT NULL
  );

  CREATE TABLE coupons (
    code TEXT PRIMARY KEY,
    discount_percent INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    min_order_usd REAL NOT NULL DEFAULT 0.0,
    expiry_date TEXT NOT NULL
  );

  CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    items TEXT NOT NULL,
    subtotal REAL NOT NULL,
    discount REAL NOT NULL,
    shipping REAL NOT NULL,
    total REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',
    created_at TEXT NOT NULL
  );
`);

// Insert Users
const insertUser = db.prepare("INSERT INTO users (id, email, password, role) VALUES (?, ?, ?, ?)");
insertUser.run("U01", "testuser@example.com", "Password123!", "user");
insertUser.run("U02", "admin@example.com", "AdminPass123!", "admin");

// Insert 10 Products
const insertProduct = db.prepare(
  "INSERT INTO products (id, name, category, price, stock, rating, description) VALUES (?, ?, ?, ?, ?, ?, ?)"
);
insertProduct.run("P01", "Quantum Pro Laptop", "Laptops", 1299.00, 15, 4.8, "High performance workstation with 32GB RAM.");
insertProduct.run("P02", "AeroBook Ultra 14", "Laptops", 999.00, 8, 4.6, "Featherweight laptop for developers and students.");
insertProduct.run("P03", "Titan Gaming Rig X", "Laptops", 1999.00, 4, 4.9, "Extreme performance gaming laptop with RTX 4080.");
insertProduct.run("P04", "SonicANC Wireless Headphones", "Audio", 199.00, 25, 4.7, "Premium noise cancelling over-ear headphones.");
insertProduct.run("P05", "PulseStudio Earbuds Pro", "Audio", 129.00, 30, 4.5, "True wireless earbuds with spatial audio.");
insertProduct.run("P06", "BassMax Portable Speaker", "Audio", 79.00, 0, 4.2, "Waterproof Bluetooth speaker (currently out of stock).");
insertProduct.run("P07", "ErgoPrecision Wireless Mouse", "Accessories", 49.00, 50, 4.8, "Ergonomic wireless mouse with precision scroll.");
insertProduct.run("P08", "MechTactile Mechanical Keyboard", "Accessories", 119.00, 20, 4.9, "Custom mechanical keyboard with tactile switches.");
insertProduct.run("P09", "ClearView 4K Monitor 27\"", "Accessories", 349.00, 12, 4.6, "Ultra-clear 4K IPS panel with HDR400.");
insertProduct.run("P10", "USB-C Dual 4K Docking Station", "Accessories", 89.00, 18, 4.4, "Versatile docking station with 100W power delivery.");

// Insert Coupons
const insertCoupon = db.prepare(
  "INSERT INTO coupons (code, discount_percent, is_active, min_order_usd, expiry_date) VALUES (?, ?, ?, ?, ?)"
);
insertCoupon.run("SAVE20", 20, 1, 0.0, "2030-12-31");
insertCoupon.run("SAVE10", 10, 1, 0.0, "2030-12-31");
insertCoupon.run("EXPIRED50", 50, 0, 0.0, "2024-01-01");

// Insert Seed Orders
const insertOrder = db.prepare(
  "INSERT INTO orders (id, user_email, items, subtotal, discount, shipping, total, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
);
insertOrder.run("ORD-1001", "testuser@example.com", JSON.stringify([{ id: "P01", qty: 1 }]), 1299.00, 0.00, 15.00, 1314.00, "Pending", "2026-10-18T10:00:00Z");
insertOrder.run("ORD-1002", "testuser@example.com", JSON.stringify([{ id: "P04", qty: 1 }]), 199.00, 39.80, 15.00, 174.20, "Processing", "2026-10-18T14:30:00Z");
insertOrder.run("ORD-1003", "customer@example.com", JSON.stringify([{ id: "P09", qty: 1 }]), 349.00, 0.00, 15.00, 364.00, "Shipped", "2026-10-17T09:15:00Z");

console.log("Seeding complete: 2 users, 10 products, 3 coupons, 3 orders.");
db.close();
