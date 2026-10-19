import Link from "next/link";

export default function HomePage() {
  return (
    <div className="py-12 space-y-8">
      <div className="text-center space-y-4 max-w-2xl mx-auto">
        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
          Welcome to TechStore
        </h1>
        <p className="text-lg text-slate-400">
          The autonomous requirements verification benchmark application. Complete with deterministic seeding, multi-step checkout, and administrator controls.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-8">
        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <h2 className="text-xl font-bold text-white">Product Catalog</h2>
          <p className="text-sm text-slate-400">
            Browse hardware and accessories with real-time category filtering and inventory status.
          </p>
          <Link
            href="/products"
            className="inline-block mt-2 text-sm font-semibold text-cyan-400 hover:text-cyan-300"
            aria-label="Explore Products"
          >
            Explore Products →
          </Link>
        </div>

        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <h2 className="text-xl font-bold text-white">Cart & Discounts</h2>
          <p className="text-sm text-slate-400">
            Review shopping cart items, test coupon codes such as SAVE20, and calculate shipping.
          </p>
          <Link
            href="/cart"
            className="inline-block mt-2 text-sm font-semibold text-cyan-400 hover:text-cyan-300"
            aria-label="View Shopping Cart"
          >
            View Shopping Cart →
          </Link>
        </div>

        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <h2 className="text-xl font-bold text-white">Admin Operations</h2>
          <p className="text-sm text-slate-400">
            Fulfill and update customer order status across the operational lifecycle.
          </p>
          <Link
            href="/admin/orders"
            className="inline-block mt-2 text-sm font-semibold text-cyan-400 hover:text-cyan-300"
            aria-label="Manage Orders"
          >
            Manage Orders →
          </Link>
        </div>
      </div>
    </div>
  );
}
