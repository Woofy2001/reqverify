"use client";

import { useEffect, useState } from "react";
import { Order } from "@/lib/db";

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [updateNotice, setUpdateNotice] = useState<string | null>(null);

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const res = await fetch("/api/orders");
      const data = await res.json();
      if (data.orders) {
        setOrders(data.orders);
      }
    } catch (err) {
      console.error("Failed to load orders", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (orderId: string, newStatus: string) => {
    try {
      const res = await fetch("/api/orders", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order_id: orderId, status: newStatus }),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setOrders((prev) =>
          prev.map((ord) => (ord.id === orderId ? { ...ord, status: newStatus } : ord))
        );
        setUpdateNotice(`Order ${orderId} updated to ${newStatus}`);
        setTimeout(() => setUpdateNotice(null), 3500);
      }
    } catch (err) {
      console.error("Failed to update status", err);
    }
  };

  return (
    <div className="space-y-8">
      <div className="border-b border-slate-800 pb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Admin Order Fulfillment
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage and transition customer orders across the operational fulfillment pipeline
          </p>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800">
          Admin Role Verified
        </span>
      </div>

      {updateNotice && (
        <div
          role="status"
          className="p-3.5 rounded-lg bg-emerald-950/70 border border-emerald-800 text-emerald-200 text-sm font-medium"
        >
          {updateNotice}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading orders...</div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-sm" aria-label="Customer Orders Table">
            <thead className="bg-slate-950/60 text-slate-400 uppercase text-xs font-semibold border-b border-slate-800">
              <tr>
                <th scope="col" className="px-6 py-4">Order ID</th>
                <th scope="col" className="px-6 py-4">Customer Email</th>
                <th scope="col" className="px-6 py-4">Date</th>
                <th scope="col" className="px-6 py-4">Total</th>
                <th scope="col" className="px-6 py-4">Status</th>
                <th scope="col" className="px-6 py-4 text-right">Fulfillment Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {orders.map((ord) => (
                <tr key={ord.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="px-6 py-4 font-mono font-bold text-cyan-400">{ord.id}</td>
                  <td className="px-6 py-4 text-slate-200">{ord.user_email}</td>
                  <td className="px-6 py-4 text-slate-400 text-xs">
                    {new Date(ord.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 font-bold text-white">${ord.total.toFixed(2)}</td>
                  <td className="px-6 py-4">
                    <span
                      role="status"
                      aria-label={`Status: ${ord.status}`}
                      className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold ${
                        ord.status === "Delivered"
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : ord.status === "Shipped"
                          ? "bg-blue-950 text-blue-400 border border-blue-800"
                          : ord.status === "Processing"
                          ? "bg-amber-950 text-amber-400 border border-amber-800"
                          : "bg-slate-800 text-slate-300 border border-slate-700"
                      }`}
                    >
                      {ord.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <select
                      aria-label={`Update status for ${ord.id}`}
                      value={ord.status}
                      onChange={(e) => handleStatusChange(ord.id, e.target.value)}
                      className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:ring-2 focus:ring-cyan-500"
                    >
                      <option value="Pending">Pending</option>
                      <option value="Processing">Processing</option>
                      <option value="Shipped">Shipped</option>
                      <option value="Delivered">Delivered</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
