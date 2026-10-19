"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Product } from "@/lib/db";
import { isMutantActive } from "@/lib/mutants";

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [category, setCategory] = useState("All");
  const [maxPrice, setMaxPrice] = useState("");
  const [cartCount, setCartCount] = useState(0);
  const [addedNotice, setAddedNotice] = useState<string | null>(null);

  useEffect(() => {
    fetchProducts();
    updateCartCount();
  }, [category, maxPrice]);

  const updateCartCount = () => {
    try {
      const items = JSON.parse(localStorage.getItem("techstore_cart") || "[]");
      const total = items.reduce((sum: number, it: any) => sum + (it.qty || 1), 0);
      setCartCount(total);
    } catch {
      setCartCount(0);
    }
  };

  const fetchProducts = async () => {
    try {
      const params = new URLSearchParams();
      if (category && category !== "All") params.append("category", category);
      if (maxPrice) params.append("maxPrice", maxPrice);

      const res = await fetch(`/api/products?${params.toString()}`);
      const data = await res.json();
      if (data.products) {
        setProducts(data.products);
      }
    } catch (err) {
      console.error("Failed to load products", err);
    }
  };

  const addToCart = (product: Product) => {
    try {
      const currentCart = JSON.parse(localStorage.getItem("techstore_cart") || "[]");
      const existing = currentCart.find((it: any) => it.id === product.id);
      if (existing) {
        existing.qty += 1;
      } else {
        currentCart.push({ ...product, qty: 1 });
      }
      localStorage.setItem("techstore_cart", JSON.stringify(currentCart));
      updateCartCount();
      setAddedNotice(`Added ${product.name} to cart!`);
      setTimeout(() => setAddedNotice(null), 3000);
    } catch (err) {
      console.error("Error adding to cart", err);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Product Catalog
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Filter devices and accessories verified for research workloads
          </p>
        </div>

        <Link
          href="/cart"
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-slate-900 border border-slate-700 hover:border-slate-600 text-sm font-medium text-white"
          aria-label={`View Cart with ${cartCount} items`}
        >
          <span>Shopping Cart</span>
          <span className="px-2 py-0.5 rounded-full bg-cyan-600 text-xs font-bold">
            {cartCount}
          </span>
        </Link>
      </div>

      {addedNotice && (
        <div
          role="status"
          className="p-3 rounded-lg bg-emerald-950/70 border border-emerald-800 text-emerald-200 text-sm font-medium transition-all"
        >
          {addedNotice}
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-wrap gap-4 items-center">
        <div className="flex items-center space-x-2">
          <label htmlFor="category-filter" className="text-sm font-medium text-slate-300">
            Category:
          </label>
          <select
            id="category-filter"
            aria-label="Filter by category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
          >
            <option value="All">All Categories</option>
            <option value="Laptops">Laptops</option>
            <option value="Audio">Audio</option>
            <option value="Accessories">Accessories</option>
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <label htmlFor="price-filter" className="text-sm font-medium text-slate-300">
            Max Price ($):
          </label>
          <input
            id="price-filter"
            type="number"
            aria-label="Filter by maximum price"
            placeholder="e.g. 500"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            className="w-32 px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
          />
        </div>

        {(category !== "All" || maxPrice !== "") && (
          <button
            onClick={() => {
              setCategory("All");
              setMaxPrice("");
            }}
            className="text-xs text-slate-400 hover:text-white underline ml-auto"
            aria-label="Reset filters"
          >
            Reset filters
          </button>
        )}
      </div>

      {/* Products Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((product) => (
          <div
            key={product.id}
            className="p-6 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between space-y-4 hover:border-slate-700 transition-all"
          >
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                  {product.category}
                </span>
                {/* M04 Defect: Suppress 'Out of stock' badge when stock=0 */}
                {(!isMutantActive("M04") || product.stock > 0) && (
                  <span
                    role="status"
                    aria-label={product.stock > 0 ? `In Stock (${product.stock})` : "Out of stock"}
                    className={`text-xs font-medium px-2 py-0.5 rounded ${
                      product.stock > 0
                        ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/60"
                        : "bg-rose-950/80 text-rose-300 border border-rose-800/60"
                    }`}
                  >
                    {product.stock > 0 ? `In Stock (${product.stock})` : "Out of stock"}
                  </span>
                )}
              </div>

              <h3 className="text-lg font-bold text-white tracking-tight">
                {product.name}
              </h3>
              <p className="text-xs text-slate-400 line-clamp-2">
                {product.description}
              </p>
            </div>

            <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-400 block">Price</span>
                <span className="text-xl font-extrabold text-white">
                  ${product.price.toFixed(2)}
                </span>
              </div>

              <button
                disabled={product.stock === 0}
                onClick={() => addToCart(product)}
                aria-label={`Add ${product.name} to cart`}
                className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-sm font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-cyan-400 disabled:cursor-not-allowed"
              >
                Add to cart
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
