"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface CartItem {
  id: string;
  name: string;
  price: number;
  qty: number;
}

export default function CartPage() {
  const router = useRouter();
  const [items, setItems] = useState<CartItem[]>([]);
  const [couponCode, setCouponCode] = useState("");
  const [discountPercent, setDiscountPercent] = useState(0);
  const [appliedCoupon, setAppliedCoupon] = useState<string | null>(null);
  const [couponError, setCouponError] = useState<string | null>(null);
  const [couponSuccess, setCouponSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadCart();
  }, []);

  const loadCart = () => {
    try {
      const stored = JSON.parse(localStorage.getItem("techstore_cart") || "[]");
      setItems(stored);
    } catch {
      setItems([]);
    }
  };

  const saveCart = (newItems: CartItem[]) => {
    setItems(newItems);
    localStorage.setItem("techstore_cart", JSON.stringify(newItems));
  };

  const updateQuantity = (id: string, delta: number) => {
    const updated = items
      .map((item) => {
        if (item.id === id) {
          const newQty = item.qty + delta;
          return newQty > 0 ? { ...item, qty: newQty } : null;
        }
        return item;
      })
      .filter((it): it is CartItem => it !== null);

    saveCart(updated);
  };

  const removeItem = (id: string) => {
    saveCart(items.filter((it) => it.id !== id));
  };

  const applyDiscount = async () => {
    setCouponError(null);
    setCouponSuccess(null);

    if (!couponCode.trim()) {
      setCouponError("Please enter a discount code.");
      return;
    }

    try {
      const res = await fetch("/api/coupons", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: couponCode.trim() }),
      });

      const data = await res.json();
      if (!res.ok || !data.valid) {
        setCouponError(data.error || "Invalid discount code.");
        setDiscountPercent(0);
        setAppliedCoupon(null);
        return;
      }

      setDiscountPercent(data.discount_percent);
      setAppliedCoupon(data.code);
      setCouponSuccess(data.message);
    } catch {
      setCouponError("Failed to apply discount code.");
    }
  };

  const subtotal = items.reduce((acc, item) => acc + item.price * item.qty, 0);
  const discountAmount = (subtotal * discountPercent) / 100.0;
  const shipping = items.length > 0 ? 15.0 : 0.0;
  const total = Math.max(0, subtotal - discountAmount + shipping);

  const proceedToCheckout = () => {
    // Persist active cart checkout calculation in localStorage
    localStorage.setItem(
      "techstore_checkout_summary",
      JSON.stringify({ subtotal, discountAmount, discountPercent, shipping, total, appliedCoupon })
    );
    window.location.href = "/checkout";
  };

  return (
    <div className="space-y-8">
      <div className="border-b border-slate-800 pb-6">
        <h1 className="text-3xl font-bold tracking-tight text-white">
          Your Shopping Cart
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Review items, adjust quantities, and apply promotional vouchers
        </p>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-2xl space-y-4">
          <p className="text-slate-400 text-lg">Your shopping cart is currently empty.</p>
          <Link
            href="/products"
            className="inline-block px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm transition-all"
            aria-label="Browse Products"
          >
            Browse Products
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Cart Items List */}
          <div className="lg:col-span-2 space-y-4">
            {items.map((item) => (
              <div
                key={item.id}
                className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <h3 className="font-bold text-white text-base">{item.name}</h3>
                  <p className="text-sm text-cyan-400 font-semibold">${item.price.toFixed(2)}</p>
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => updateQuantity(item.id, -1)}
                    aria-label={`Decrease quantity for ${item.name}`}
                    className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-bold flex items-center justify-center border border-slate-700 transition-colors"
                  >
                    -
                  </button>

                  <span
                    aria-label={`Quantity of ${item.name}`}
                    className="w-10 text-center font-bold text-white text-sm"
                  >
                    {item.qty}
                  </span>

                  <button
                    onClick={() => updateQuantity(item.id, 1)}
                    aria-label={`Increase quantity for ${item.name}`}
                    className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-bold flex items-center justify-center border border-slate-700 transition-colors"
                  >
                    +
                  </button>

                  <button
                    onClick={() => removeItem(item.id)}
                    aria-label={`Remove ${item.name} from cart`}
                    className="ml-2 text-xs text-rose-400 hover:text-rose-300 font-medium px-2 py-1 rounded hover:bg-rose-950/40"
                  >
                    Remove item
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Order Summary & Coupon */}
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
              <h2 className="text-lg font-bold text-white border-b border-slate-800 pb-3">
                Order Summary
              </h2>

              <div className="space-y-2.5 text-sm">
                <div className="flex justify-between text-slate-300">
                  <span>Subtotal:</span>
                  <span className="font-semibold text-white">${subtotal.toFixed(2)}</span>
                </div>

                {discountPercent > 0 && (
                  <div className="flex justify-between text-emerald-400 font-medium">
                    <span>Discount ({discountPercent}%):</span>
                    <span>-${discountAmount.toFixed(2)}</span>
                  </div>
                )}

                <div className="flex justify-between text-slate-300">
                  <span>Shipping:</span>
                  <span className="font-semibold text-white">${shipping.toFixed(2)}</span>
                </div>

                <div className="border-t border-slate-800 pt-3 flex justify-between text-base font-bold text-white">
                  <span>Estimated Total:</span>
                  <span className="text-cyan-400">${total.toFixed(2)}</span>
                </div>
              </div>

              {/* Discount Code Input */}
              <div className="pt-4 border-t border-slate-800 space-y-2">
                <label htmlFor="discount-code" className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Discount code
                </label>
                <div className="flex space-x-2">
                  <input
                    id="discount-code"
                    type="text"
                    aria-label="Discount code"
                    placeholder="e.g. SAVE20"
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value)}
                    className="flex-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 uppercase"
                  />
                  <button
                    onClick={applyDiscount}
                    aria-label="Apply Discount"
                    className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-sm font-semibold border border-slate-700 transition-all"
                  >
                    Apply Discount
                  </button>
                </div>

                {couponError && (
                  <div role="alert" className="text-xs text-rose-400 mt-1">
                    {couponError}
                  </div>
                )}
                {couponSuccess && (
                  <div role="status" className="text-xs text-emerald-400 mt-1 font-medium">
                    {couponSuccess}
                  </div>
                )}
              </div>

              <button
                onClick={proceedToCheckout}
                aria-label="Proceed to Checkout"
                className="w-full py-3 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm transition-all focus:outline-none focus:ring-2 focus:ring-cyan-400 shadow-lg shadow-cyan-950"
              >
                Proceed to Checkout
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
