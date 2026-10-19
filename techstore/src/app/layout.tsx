import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "TechStore Portal",
  description: "Benchmark System Under Test for ReqVerify Autonomous Requirements Verification",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
        <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-8">
              <Link
                href="/"
                className="text-xl font-bold tracking-tight text-white hover:text-cyan-400 transition-colors"
                aria-label="TechStore Home"
              >
                TechStore
              </Link>
              <nav className="flex space-x-6 text-sm font-medium" aria-label="Main Navigation">
                <Link
                  href="/products"
                  className="text-slate-300 hover:text-white transition-colors"
                  aria-label="Products"
                >
                  Products
                </Link>
                <Link
                  href="/cart"
                  className="text-slate-300 hover:text-white transition-colors"
                  aria-label="Cart"
                >
                  Cart
                </Link>
                <Link
                  href="/admin/orders"
                  className="text-slate-300 hover:text-white transition-colors"
                  aria-label="Admin"
                >
                  Admin
                </Link>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/login"
                className="text-sm font-medium px-4 py-2 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white transition-all border border-slate-700"
                aria-label="Sign in"
              >
                Sign in
              </Link>
            </div>
          </div>
        </header>

        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="border-t border-slate-800 bg-slate-900 py-6 text-center text-xs text-slate-500">
          <p>© 2026 TechStore Research SUT — ReqVerify Benchmark Portal</p>
        </footer>
      </body>
    </html>
  );
}
