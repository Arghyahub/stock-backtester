"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import AccountNav from "@/components/auth/account-nav";
import Api from "@/utils/api/api";

type Position = { ticker: string; quantity: number; average_cost: number; target_price: number; close: number | null; purchase_count: number };
type Portfolio = { positions: Position[]; signal: { action: { type: "buy" | "average" | "sell" | "none"; ticker: string | null }; sell_tickers: string[]; average_ticker: string | null } };

export default function ActionsPage() {
  const [signedIn, setSignedIn] = useState<boolean>();
  const [portfolio, setPortfolio] = useState<Portfolio>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try { const result = await Api.get("/midcap-shop/portfolio"); if (!result.ok) throw new Error(result.detail || "Unable to refresh your Midcap SHOP actions"); setPortfolio(result as Portfolio); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to refresh your actions"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const initialize = async () => {
    if (!localStorage.getItem("token")) { setSignedIn(false); setLoading(false); return; }
    const account = await Api.get("/user/me");
    if (!account.ok) { localStorage.removeItem("token"); setSignedIn(false); setLoading(false); return; }
    setSignedIn(true); void refresh();
  }; void initialize(); }, [refresh]);
  if (signedIn === undefined) return <main className="min-h-screen bg-surface-primary p-6 md:p-12">Loading your actions…</main>;
  if (!signedIn) return <main className="min-h-screen bg-surface-primary p-6 md:p-12"><section className="mx-auto max-w-lg rounded-lg border border-outline-variant bg-surface-container-lowest p-6"><Link className="text-sm text-brand-primary" href="/">← Strategies</Link><h1 className="mt-4 text-3xl font-bold">Your actions</h1><p className="mt-2 text-on-surface-variant">Log in to check actions for stocks you have recorded.</p><Link className="mt-5 inline-block rounded bg-brand-primary px-4 py-2 text-white" href="/login">Log in</Link></section></main>;
  const signal = portfolio?.signal;
  const headline = signal?.action.type === "sell" ? `Sell ${signal.action.ticker}` : signal?.action.type === "average" ? `Average ${signal.action.ticker}` : signal?.action.type === "buy" ? `Fresh buy ${signal.action.ticker}` : "No eligible action";
  return <main className="min-h-screen bg-surface-primary p-6 md:p-12"><div className="mx-auto max-w-6xl"><header className="flex items-start justify-between gap-4 border-b border-outline-variant pb-6"><div><Link className="text-sm text-brand-primary" href="/">← Strategies</Link><h1 className="mt-4 text-3xl font-bold">Actions</h1><p className="mt-2 text-on-surface-variant">Only stocks you have recorded are checked here.</p></div><AccountNav /></header><section className="mt-8 rounded-lg border border-outline-variant bg-surface-container-lowest p-5"><div className="flex items-start justify-between gap-4"><div><p className="text-sm font-medium text-brand-primary">MIDCAP SHOP</p><h2 className="mt-1 text-xl font-semibold">My saved stocks</h2><p className="mt-1 text-sm text-on-surface-variant">Refreshes only your database-backed holdings against the latest completed daily scan.</p></div><button className="rounded border border-outline-variant px-3 py-2 text-sm disabled:opacity-50" disabled={loading} onClick={() => void refresh()}>{loading ? "Refreshing…" : "Refresh"}</button></div>{error ? <p className="mt-4 text-sm text-red-700">{error}</p> : loading ? <p className="mt-4 text-sm text-on-surface-variant">Checking your saved stocks…</p> : !portfolio?.positions.length ? <div className="mt-5 rounded border border-outline-variant p-4"><p className="font-medium">No saved stocks</p><p className="mt-1 text-sm text-on-surface-variant">Record a Midcap SHOP buy first; it will appear here only after it is saved to your account.</p><Link className="mt-3 inline-block text-sm font-medium text-brand-primary" href="/midcap-shop">Open Midcap SHOP →</Link></div> : <><div className="mt-5 rounded border border-brand-primary p-4"><p className="text-sm font-medium text-brand-primary">Current action</p><p className="mt-1 font-semibold">{headline}</p><p className="mt-1 text-sm text-on-surface-variant">Sell takes priority over averaging; averaging takes priority over a new entry.</p></div><div className="mt-4 space-y-3">{portfolio.positions.map((item) => { const status = signal?.sell_tickers.includes(item.ticker) ? "Sell chance" : signal?.average_ticker === item.ticker ? "Averaging chance" : "Held"; return <article className="rounded border border-outline-variant p-4" key={item.ticker}><div className="flex justify-between gap-3"><b>{item.ticker}</b><span className="text-sm font-medium">{status}</span></div><p className="mt-1 text-sm">{item.quantity} shares · Average ₹{item.average_cost.toFixed(2)} · Target ₹{item.target_price.toFixed(2)}</p><p className="mt-1 text-xs text-on-surface-variant">Latest scan close: {item.close == null ? "not in today’s shortlist" : `₹${item.close.toFixed(2)}`} · {item.purchase_count}/4 purchases</p></article>; })}</div><Link className="mt-5 inline-block text-sm font-medium text-brand-primary" href="/midcap-shop">Open Midcap SHOP →</Link></>}</section><section className="mt-6 rounded-lg border border-outline-variant bg-surface-container-lowest p-5"><p className="text-sm font-medium text-brand-primary">SEASONAL RESEARCH</p><h2 className="mt-1 text-xl font-semibold">No saved stock positions</h2><p className="mt-2 text-sm text-on-surface-variant">Seasonal Research does not currently record stock purchases, so no calendar opportunities are shown here. This dashboard will list it only when you save a Seasonal Research position.</p></section></div></main>;
}
