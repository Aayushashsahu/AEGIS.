/** AEGIS status badge: status is expressed in text before color. */
import type { LifecycleStatus } from "@/lib/lifecycle";

export function StatusBadge({ status }: { status: LifecycleStatus }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}>{status.replaceAll("_", " ")}</span>;
}
