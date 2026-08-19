/**
 * Round 4 radial sensing system: global chrome stays deliberately quiet; lifecycle topology belongs only to evidence-bearing workspaces.
 */
import { Link, useLocation } from "wouter";
import { AegisMark } from "./AegisMark";
import { ArrowUpRight, Circle } from "lucide-react";

const navItems = [
  { href: "/cases", label: "Cases" },
  { href: "/evidence", label: "Evidence" },
  { href: "/judge", label: "Judge Mode" },
  { href: "/benchmark", label: "Benchmark" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const context = navItems.find((item) => location === item.href || location.startsWith(`${item.href}/`))?.label ?? "Protect a scraper";
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link href="/" className="brand-lockup" aria-label="AEGIS home">
          <AegisMark size={38} />
          <span className="brand-name"><span className="cut-a">A</span>EGIS</span>
        </Link>

        <nav className="primary-nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link ${location === item.href ? "is-active" : ""}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="topbar-actions">
          <span className="system-status"><Circle size={8} fill="currentColor" /> {context} / evidence control</span>
          <Link href="/#create" className="new-case-link">
            <span>New case</span><ArrowUpRight size={16} />
          </Link>
        </div>
      </header>
      <div className="route-instrument-rail" aria-label={`Current location: ${context}`}><span>AEGIS</span><i /><b>{context}</b><i /><span>Evidence control</span></div>
      {children}
    </div>
  );
}
