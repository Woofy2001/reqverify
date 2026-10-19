"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

export default function CheckoutPage() {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Form Fields
  const [fullName, setFullName] = useState("Jane Doe");
  const [streetAddress, setStreetAddress] = useState("123 Research Way");
  const [city, setCity] = useState("Tech City");
  const [stateProv, setStateProv] = useState("California");
  const [postalCode, setPostalCode] = useState("94016");
  const [billingMatches, setBillingMatches] = useState(true);

  // Payment Fields
  const [cardName, setCardName] = useState("Jane Doe");
  const [cardNumber, setCardNumber] = useState("4111 2222 3333 4444");
  const [expDate, setExpDate] = useState("12/28");
  const [cvc, setCvc] = useState("123");

  // Summary & Submission
  const [summary, setSummary] = useState<any>({ subtotal: 0, discountAmount: 0, shipping: 15.0, total: 15.0 });
  const [orderResult, setOrderResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    try {
      const storedSummary = JSON.parse(localStorage.getItem("techstore_checkout_summary") || "{}");
      if (storedSummary.subtotal) {
        setSummary(storedSummary);
      }
    } catch {
      // default summary
    }
  }, []);

  const handlePlaceOrder = async () => {
    setError(null);
    setLoading(true);

    try {
      const cartItems = JSON.parse(localStorage.getItem("techstore_cart") || "[]");
      const user = JSON.parse(localStorage.getItem("techstore_user") || '{"email": "testuser@example.com"}');

      const res = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_email: user.email,
          items: cartItems,
          subtotal: summary.subtotal,
          discount: summary.discountAmount,
          shipping: summary.shipping,
          total: summary.total,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Failed to place order.");
        setLoading(false);
        return;
      }

      // Clear shopping cart on successful checkout
      localStorage.removeItem("techstore_cart");
      localStorage.removeItem("techstore_checkout_summary");

      setOrderResult(data);
      setStep(4);
    } catch (err: any) {
      setError("An unexpected network error occurred while placing order.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 py-6">
      <div className="border-b border-slate-800 pb-6">
        <h1 className="text-3xl font-bold tracking-tight text-white">Checkout</h1>
        <p className="text-sm text-slate-400 mt-1">
          Complete shipping and payment details to finalize your research equipment purchase
        </p>
      </div>

      {/* Checkout Step Wizard Indicator */}
      <nav aria-label="Checkout steps" className="flex items-center justify-between border border-slate-800 rounded-xl p-4 bg-slate-900">
        <div className={`flex items-center space-x-2 ${step >= 1 ? "text-cyan-400 font-bold" : "text-slate-500"}`}>
          <span className="w-6 h-6 rounded-full border border-current flex items-center justify-center text-xs">1</span>
          <span className="text-sm">Shipping Address</span>
        </div>
        <div className="h-px w-12 bg-slate-800"></div>
        <div className={`flex items-center space-x-2 ${step >= 2 ? "text-cyan-400 font-bold" : "text-slate-500"}`}>
          <span className="w-6 h-6 rounded-full border border-current flex items-center justify-center text-xs">2</span>
          <span className="text-sm">Payment Method</span>
        </div>
        <div className="h-px w-12 bg-slate-800"></div>
        <div className={`flex items-center space-x-2 ${step >= 3 ? "text-cyan-400 font-bold" : "text-slate-500"}`}>
          <span className="w-6 h-6 rounded-full border border-current flex items-center justify-center text-xs">3</span>
          <span className="text-sm">Review & Place Order</span>
        </div>
      </nav>

      {error && (
        <div role="alert" className="p-3.5 rounded-lg bg-rose-950/70 border border-rose-800 text-rose-200 text-sm">
          {error}
        </div>
      )}

      {/* STEP 1: Shipping Address */}
      {step === 1 && (
        <div className="p-8 rounded-xl bg-slate-900 border border-slate-800 space-y-6">
          <h2 className="text-xl font-bold text-white">Shipping Address</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2 space-y-1.5">
              <label htmlFor="fullname" className="block text-xs font-semibold text-slate-300">
                Full name
              </label>
              <input
                id="fullname"
                type="text"
                aria-label="Full name"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div className="md:col-span-2 space-y-1.5">
              <label htmlFor="street" className="block text-xs font-semibold text-slate-300">
                Street address
              </label>
              <input
                id="street"
                type="text"
                aria-label="Street address"
                required
                value={streetAddress}
                onChange={(e) => setStreetAddress(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="city" className="block text-xs font-semibold text-slate-300">
                City
              </label>
              <input
                id="city"
                type="text"
                aria-label="City"
                required
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="state" className="block text-xs font-semibold text-slate-300">
                State / Province
              </label>
              <select
                id="state"
                aria-label="State / Province"
                value={stateProv}
                onChange={(e) => setStateProv(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:ring-2 focus:ring-cyan-500"
              >
                <option value="California">California</option>
                <option value="New York">New York</option>
                <option value="Texas">Texas</option>
                <option value="Washington">Washington</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="postal" className="block text-xs font-semibold text-slate-300">
                Postal code
              </label>
              <input
                id="postal"
                type="text"
                aria-label="Postal code"
                required
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div className="md:col-span-2 pt-2 flex items-center space-x-2">
              <input
                id="billing-match"
                type="checkbox"
                aria-label="Billing address matches shipping address"
                checked={billingMatches}
                onChange={(e) => setBillingMatches(e.target.checked)}
                className="w-4 h-4 rounded text-cyan-600 focus:ring-cyan-500 bg-slate-950 border-slate-700"
              />
              <label htmlFor="billing-match" className="text-sm text-slate-300">
                Billing address matches shipping address
              </label>
            </div>
          </div>

          <button
            onClick={() => {
              if (!fullName || !streetAddress || !city || !postalCode) {
                setError("Please fill out all required address fields.");
                return;
              }
              setError(null);
              setStep(2);
            }}
            aria-label="Continue to Payment"
            className="w-full py-3 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm transition-all focus:ring-2 focus:ring-cyan-400"
          >
            Continue to Payment
          </button>
        </div>
      )}

      {/* STEP 2: Payment Method */}
      {step === 2 && (
        <div className="p-8 rounded-xl bg-slate-900 border border-slate-800 space-y-6">
          <h2 className="text-xl font-bold text-white">Payment Method</h2>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="cardname" className="block text-xs font-semibold text-slate-300">
                Cardholder name
              </label>
              <input
                id="cardname"
                type="text"
                aria-label="Cardholder name"
                required
                value={cardName}
                onChange={(e) => setCardName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="cardnum" className="block text-xs font-semibold text-slate-300">
                Card number
              </label>
              <input
                id="cardnum"
                type="text"
                aria-label="Card number"
                required
                value={cardNumber}
                onChange={(e) => setCardNumber(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label htmlFor="expdate" className="block text-xs font-semibold text-slate-300">
                  Expiration date
                </label>
                <input
                  id="expdate"
                  type="text"
                  aria-label="Expiration date"
                  placeholder="MM/YY"
                  required
                  value={expDate}
                  onChange={(e) => setExpDate(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:ring-2 focus:ring-cyan-500"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="cvc" className="block text-xs font-semibold text-slate-300">
                  CVC
                </label>
                <input
                  id="cvc"
                  type="password"
                  aria-label="CVC"
                  maxLength={4}
                  required
                  value={cvc}
                  onChange={(e) => setCvc(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:ring-2 focus:ring-cyan-500"
                />
              </div>
            </div>
          </div>

          <div className="flex space-x-4 pt-2">
            <button
              onClick={() => setStep(1)}
              aria-label="Back to Shipping"
              className="w-1/3 py-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm border border-slate-700"
            >
              Back to Shipping
            </button>
            <button
              onClick={() => {
                if (!cardName || !cardNumber || !expDate || !cvc) {
                  setError("Please fill out all required payment details.");
                  return;
                }
                setError(null);
                setStep(3);
              }}
              aria-label="Continue to Review"
              className="w-2/3 py-3 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm transition-all focus:ring-2 focus:ring-cyan-400"
            >
              Continue to Review
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Review & Place Order */}
      {step === 3 && (
        <div className="p-8 rounded-xl bg-slate-900 border border-slate-800 space-y-6">
          <h2 className="text-xl font-bold text-white">Review & Place Order</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-4 rounded-lg bg-slate-950 border border-slate-800 text-sm">
            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Ship to:</span>
              <p className="text-white font-medium mt-1">{fullName}</p>
              <p className="text-slate-400">{streetAddress}, {city}, {stateProv} {postalCode}</p>
            </div>
            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Payment:</span>
              <p className="text-white font-medium mt-1">Card ending in {cardNumber.slice(-4)}</p>
              <p className="text-slate-400">Exp: {expDate}</p>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2 text-sm">
            <div className="flex justify-between text-slate-300">
              <span>Subtotal:</span>
              <span className="text-white font-semibold">${summary.subtotal.toFixed(2)}</span>
            </div>
            {summary.discountAmount > 0 && (
              <div className="flex justify-between text-emerald-400">
                <span>Discount:</span>
                <span>-${summary.discountAmount.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between text-slate-300">
              <span>Shipping:</span>
              <span className="text-white font-semibold">${summary.shipping.toFixed(2)}</span>
            </div>
            <div className="border-t border-slate-800 pt-2 flex justify-between text-base font-bold text-white">
              <span>Total:</span>
              <span className="text-cyan-400">${summary.total.toFixed(2)}</span>
            </div>
          </div>

          <div className="flex space-x-4 pt-2">
            <button
              onClick={() => setStep(2)}
              aria-label="Back to Payment"
              className="w-1/3 py-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm border border-slate-700"
            >
              Back to Payment
            </button>
            <button
              disabled={loading}
              onClick={handlePlaceOrder}
              aria-label="Place Order"
              className="w-2/3 py-3 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold text-sm transition-all shadow-lg shadow-cyan-950"
            >
              {loading ? "Placing Order..." : "Place Order"}
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: Order Confirmation */}
      {step === 4 && orderResult && (
        <div
          role="status"
          aria-label="Order Placed Successfully!"
          className="p-8 rounded-2xl bg-slate-900 border border-slate-800 text-center space-y-6"
        >
          <div className="w-16 h-16 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center justify-center mx-auto text-2xl font-bold">
            ✓
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-white">Order Placed Successfully!</h2>
            <p className="text-slate-400 text-sm">
              Thank you for your order. Your research equipment fulfillment is in progress.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 inline-block text-left text-sm space-y-1">
            <p className="text-slate-300">
              Order Reference: <strong className="text-cyan-400 font-mono">{orderResult.order_id}</strong>
            </p>
            <p className="text-slate-300">
              Initial Status: <span className="font-semibold text-emerald-400">{orderResult.status}</span>
            </p>
          </div>
          <div className="pt-4">
            <Link
              href="/products"
              className="px-6 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold transition-all inline-block"
              aria-label="Continue Shopping"
            >
              Continue Shopping
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
