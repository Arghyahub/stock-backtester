"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Api from "@/utils/api/api";
import AccountNav from "@/components/auth/account-nav";

type Instrument = {
  ticker: string;
  name: string;
  seasonal_return: number;
  alpha: number;
  beta: number;
};
type Plan = {
  plan_id: number;
  sector: string;
  entry_date: string;
  exit_date: string;
  window_days: number;
  oos_mean_return: number;
  oos_worst_return: number;
  stock?: Instrument;
  etf?: Instrument;
};
type View =
  | "calendar"
  | "upcoming"
  | "active"
  | "completed"
  | "custom"
  | "saved";
const pct = (value: number) => `${(value * 100).toFixed(2)}%`;
const savedKey = "seasonal-research-tracked-windows";

export default function Home() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [saved, setSaved] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<View>("calendar");
  const [days, setDays] = useState("30");
  const [sort, setSort] = useState<"average" | "worst" | "date">("date");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const pageSize = 24;
  useEffect(() => {
    try {
      setSaved(JSON.parse(localStorage.getItem(savedKey) || "[]"));
    } catch {
      setSaved([]);
    }
  }, []);
  useEffect(() => {
    if (view === "saved") {
      setPlans(saved);
      setTotal(saved.length);
      setLoading(false);
      return;
    }
    if (view === "custom" && (!from || !to)) {
      setPlans([]);
      setTotal(0);
      setLoading(false);
      return;
    }
    setLoading(true);
    const custom =
      view === "custom" ? `&start_date=${from}&end_date=${to}` : "";
    Api.get(
      `/anomaly/calendar?view=${view}&days=${days}&page=${page}&page_size=${pageSize}&sort=${sort}${custom}`,
    )
      .then((result) => {
        setPlans(Array.isArray(result.items) ? result.items : []);
        setTotal(Number(result.total) || 0);
      })
      .finally(() => setLoading(false));
  }, [view, days, page, sort, from, to, saved]);
  const selectView = (next: View) => {
    setView(next);
    setPage(1);
  };
  const toggleSaved = (plan: Plan) => {
    const next = saved.some((item) => item.plan_id === plan.plan_id)
      ? saved.filter((item) => item.plan_id !== plan.plan_id)
      : [...saved, plan];
    setSaved(next);
    localStorage.setItem(savedKey, JSON.stringify(next));
  };
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const isSaved = (id: number) => saved.some((item) => item.plan_id === id);
  return (
    <main className="min-h-screen bg-surface-primary p-6 md:p-12">
      <header className="mx-auto flex max-w-6xl items-center justify-between border-b border-outline-variant pb-6">
        <div>
          <Link className="text-sm text-brand-primary" href="/">
            ← Strategies
          </Link>
          <h1 className="text-3xl font-bold">Market-window calendar</h1>
        </div>
        <AccountNav />
      </header>
      <section className="mx-auto max-w-6xl py-8">
        <p className="mb-4 max-w-3xl text-on-surface-variant">
          Approved close-to-close seasonal windows. Save a window to retain its
          planned dates in this browser.
        </p>
        <div className="mb-6 flex flex-wrap gap-3">
          <label className="text-sm font-medium">
            View{" "}
            <select
              className="ml-2 rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2"
              value={view}
              onChange={(e) => selectView(e.target.value as View)}
            >
              <option value="calendar">Full calendar</option>
              <option value="upcoming">Upcoming</option>
              <option value="active">Active now</option>
              <option value="completed">Completed</option>
              <option value="custom">Custom dates</option>
              <option value="saved">My tracked windows ({saved.length})</option>
            </select>
          </label>
          {view === "upcoming" && (
            <label className="text-sm font-medium">
              Period{" "}
              <select
                className="ml-2 rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2"
                value={days}
                onChange={(e) => {
                  setDays(e.target.value);
                  setPage(1);
                }}
              >
                <option value="7">Next 7 days</option>
                <option value="30">Next 30 days</option>
                <option value="60">Next 60 days</option>
                <option value="90">Next 90 days</option>
                <option value="180">Next 180 days</option>
              </select>
            </label>
          )}
          {view === "custom" && (
            <>
              <label className="text-sm">
                From{" "}
                <input
                  className="ml-2 rounded border p-2"
                  type="date"
                  value={from}
                  onChange={(e) => {
                    setFrom(e.target.value);
                    setPage(1);
                  }}
                />
              </label>
              <label className="text-sm">
                To{" "}
                <input
                  className="ml-2 rounded border p-2"
                  type="date"
                  value={to}
                  onChange={(e) => {
                    setTo(e.target.value);
                    setPage(1);
                  }}
                />
              </label>
            </>
          )}
          <label className="text-sm font-medium">
            Sort{" "}
            <select
              className="ml-2 rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2"
              value={sort}
              onChange={(e) => {
                setSort(e.target.value as typeof sort);
                setPage(1);
              }}
            >
              <option value="date">Entry date</option>
              <option value="average">Highest OOS average return</option>
              <option value="worst">Highest worst-case return</option>
            </select>
          </label>
        </div>
        {loading ? (
          <p>Loading approved windows…</p>
        ) : plans.length === 0 ? (
          <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-8">
            <h2 className="text-xl font-semibold">No windows in this view</h2>
            <p className="mt-2 text-on-surface-variant">
              Try another date filter, or save a window from the calendar.
            </p>
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              {plans.map((plan) => (
                <div
                  key={plan.plan_id}
                  className="relative rounded-lg border border-outline-variant bg-surface-container-lowest p-5 transition hover:border-brand-primary"
                >
                  <button
                    className="absolute right-3 top-3 rounded border px-2 py-1 text-xs"
                    onClick={() => toggleSaved(plan)}
                  >
                    {isSaved(plan.plan_id) ? "Saved" : "Save"}
                  </button>
                  <Link href={`/plans/${plan.plan_id}`} className="block">
                    <div className="flex items-start justify-between gap-3 pr-16">
                      <div>
                        <h2 className="text-xl font-bold">{plan.sector}</h2>
                        <p className="text-sm text-on-surface-variant">
                          Enter {plan.entry_date} · Exit {plan.exit_date}
                        </p>
                      </div>
                      <span className="rounded bg-surface-container-low px-2 py-1 text-sm">
                        {plan.window_days} days
                      </span>
                    </div>
                    <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
                      <Metric
                        title="OOS average"
                        value={pct(plan.oos_mean_return)}
                      />
                      <Metric
                        title="Worst OOS return"
                        value={pct(plan.oos_worst_return)}
                      />
                      <InstrumentCard label="Stock" item={plan.stock} />
                      <InstrumentCard label="ETF" item={plan.etf} />
                    </div>
                  </Link>
                </div>
              ))}
            </div>
            {view !== "saved" && (
              <div className="mt-8 flex items-center justify-between">
                <p className="text-sm text-on-surface-variant">
                  Page {page} of {pages} · {total} windows
                </p>
                <div className="flex gap-2">
                  <button
                    className="rounded border px-3 py-2 text-sm disabled:opacity-40"
                    disabled={page === 1}
                    onClick={() => setPage(page - 1)}
                  >
                    Previous
                  </button>
                  <button
                    className="rounded border px-3 py-2 text-sm disabled:opacity-40"
                    disabled={page === pages}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}
function Metric({ title, value }: { title: string; value: string }) {
  return (
    <div>
      <p className="text-on-surface-variant">{title}</p>
      <p className="font-semibold">{value}</p>
    </div>
  );
}
function InstrumentCard({ label, item }: { label: string; item?: Instrument }) {
  return (
    <div>
      <p className="text-on-surface-variant">Best {label}</p>
      <p className="font-semibold">{item ? item.ticker : "Not available"}</p>
      {item && (
        <p className="text-xs text-on-surface-variant">
          α {pct(item.alpha)} · β {item.beta.toFixed(2)}
        </p>
      )}
    </div>
  );
}
