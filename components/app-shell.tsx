"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Files, MessageSquareText, ShieldCheck } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const links = [
    { href: "/", label: "Ask", icon: MessageSquareText },
    { href: "/upload", label: "Library", icon: Files }
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link href="/" className="brand" aria-label="AskDocs home">
          <span className="brand-mark">A</span>
          <span>AskDocs</span>
        </Link>
        <nav className="nav" aria-label="Primary navigation">
          {links.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className={pathname === href ? "nav-link active" : "nav-link"}>
              <Icon size={17} strokeWidth={2} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="security-pill"><ShieldCheck size={15} /> Private workspace</div>
      </header>
      <main>{children}</main>
    </div>
  );
}
