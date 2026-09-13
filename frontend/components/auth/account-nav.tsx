"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Api from "@/utils/api/api";

type Account = { email: string };

export default function AccountNav() {
  const [account, setAccount] = useState<Account | null>(null);
  useEffect(() => {
    if (!localStorage.getItem("token")) return;
    Api.get("/user/me").then((result) => {
      if (result.ok) setAccount(result as Account);
      else localStorage.removeItem("token");
    }).catch(() => localStorage.removeItem("token"));
  }, []);
  if (!account) return <div className="flex items-center gap-2"><Link className="rounded-md border border-outline-variant px-4 py-2 text-sm font-medium" href="/login">Log in</Link><Link className="rounded-md bg-brand-primary px-4 py-2 text-sm font-medium text-white" href="/signup">Sign up</Link></div>;
  return <div className="flex items-center gap-3"><Link className="rounded-md border border-outline-variant px-4 py-2 text-sm font-medium" href="/actions">Actions</Link><span className="hidden max-w-48 truncate text-sm text-on-surface-variant sm:inline">{account.email}</span><button className="rounded-md border border-outline-variant px-4 py-2 text-sm font-medium" onClick={() => { localStorage.removeItem("token"); window.location.assign("/"); }}>Log out</button></div>;
}
