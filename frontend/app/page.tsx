import Link from "next/link";
import AccountNav from "@/components/auth/account-nav";

const strategies = [
  {
    name: "Seasonal Research",
    description: "Browse approved close-to-close seasonal market windows, historical evidence, and mapped instruments.",
    href: "/seasonal-research",
    status: "Available",
  },
  {
    name: "Nifty Midcap SHOP",
    description: "Daily capped mean-reversion scan with account-backed position tracking and stock-average exit signals. Historical 2021–2025 research produced an approximate 25% XIRR.",
    href: "/midcap-shop",
    status: "Available",
  },
];

export default function StrategyHome() {
  return <main className="min-h-screen bg-surface-primary p-6 md:p-12"><header className="mx-auto flex max-w-6xl items-center justify-between border-b border-outline-variant pb-6"><div><p className="text-sm font-semibold text-brand-primary">MARKET RESEARCH</p><h1 className="text-3xl font-bold">Strategies</h1></div><AccountNav /></header><section className="mx-auto max-w-6xl py-8"><p className="max-w-2xl text-on-surface-variant">Choose a research strategy to explore its approved results. More strategies can be added here as they become available.</p><aside className="mt-5 max-w-3xl rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"><p className="font-semibold">Research-only disclaimer</p><p className="mt-1">This site does not promote or recommend buying or selling securities. The creator is not a SEBI-registered analyst. It is a collection of backtested swing-strategy research and is not investment advice.</p></aside><div className="mt-8 grid gap-4 md:grid-cols-2">{strategies.map(strategy => <Link className="rounded-lg border border-outline-variant bg-surface-container-lowest p-6 transition hover:border-brand-primary" href={strategy.href} key={strategy.href}><div className="flex items-start justify-between gap-3"><h2 className="text-xl font-bold">{strategy.name}</h2><span className="rounded bg-green-100 px-2 py-1 text-xs font-medium text-green-800">{strategy.status}</span></div><p className="mt-3 text-on-surface-variant">{strategy.description}</p><p className="mt-6 text-sm font-medium text-brand-primary">Open strategy →</p></Link>)}</div></section></main>;
}
