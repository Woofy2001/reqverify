"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { isMutantActive } from "@/lib/mutants";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    // M01 Defect: Email validation regex accepts 'a@b'
    if (isMutantActive("M01")) {
      const brokenRegex = /^[^\s@]+@[^\s@]+$/;
      if (!brokenRegex.test(email)) {
        setError("Invalid email format.");
        setLoading(false);
        return;
      }
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        setError("Invalid email format. Must include a valid domain (e.g. user@example.com)");
        setLoading(false);
        return;
      }
    }

    // M02 Defect: Minimum password length skipped
    if (!isMutantActive("M02")) {
      if (password.length < 6) {
        setError("Password must be at least 6 characters.");
        setLoading(false);
        return;
      }
    }

    try {
      const res = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Authentication failed.");
        setLoading(false);
        return;
      }

      setSuccess("Authentication successful! Redirecting...");
      setTimeout(() => {
        window.location.href = data.user?.role === "admin" ? "/admin/orders" : "/products";
      }, 200);
    } catch (err: any) {
      setError("An unexpected network error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-12">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-xl space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Sign in to TechStore
          </h1>
          <p className="text-sm text-slate-400">
            Enter your academic research credentials to continue
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="p-3 rounded-lg bg-rose-950/60 border border-rose-800/80 text-rose-200 text-sm"
          >
            {error}
          </div>
        )}

        {success && (
          <div
            role="status"
            className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800/80 text-emerald-200 text-sm"
          >
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="email" className="block text-sm font-medium text-slate-300">
              Email address
            </label>
            <input
              id="email"
              type="email"
              required
              aria-label="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="testuser@example.com"
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent text-sm"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="block text-sm font-medium text-slate-300">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              aria-label="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent text-sm"
            />
          </div>

          <div className="flex items-center justify-between text-xs">
            <a
              href="#forgot-password"
              className="text-cyan-400 hover:text-cyan-300"
              aria-label="Forgot your password?"
              onClick={(e) => {
                e.preventDefault();
                alert("For this research environment, use seeded test accounts.");
              }}
            >
              Forgot your password?
            </a>
          </div>

          <button
            type="submit"
            disabled={loading}
            aria-label="Sign in"
            className="w-full py-2.5 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm transition-all focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="pt-4 border-t border-slate-800 text-xs text-slate-400 space-y-1 bg-slate-950/40 p-3 rounded-lg">
          <p className="font-semibold text-slate-300">Seeded Research Credentials:</p>
          <p>User: <code className="text-cyan-300">testuser@example.com</code> / <code className="text-cyan-300">Password123!</code></p>
          <p>Admin: <code className="text-cyan-300">admin@example.com</code> / <code className="text-cyan-300">AdminPass123!</code></p>
        </div>
      </div>
    </div>
  );
}
