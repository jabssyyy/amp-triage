/** Shared primitives, styled from the Stitch template's Material 3 tokens. */
import type { ReactNode } from "react";
import { confidenceStyle, tierLabel, tierStyle, type Confidence, type StructureTier } from "../api";

export function Icon({ name, className = "", fill = false, size }: {
  name: string; className?: string; fill?: boolean; size?: number;
}) {
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={{ fontVariationSettings: `'FILL' ${fill ? 1 : 0}`, fontSize: size ? `${size}px` : undefined }}
    >
      {name}
    </span>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-surface-container-lowest border border-outline-variant rounded-lg ${className}`}>
      {children}
    </div>
  );
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="mb-md">
      <h2 className="font-headline-sm text-headline-sm text-on-surface">{children}</h2>
      {hint && <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">{hint}</p>}
    </div>
  );
}

export function Stat({ label, value, sub, tone = "default" }: {
  label: string; value: ReactNode; sub?: string;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  const toneClass = {
    default: "text-on-surface", good: "text-secondary",
    warn: "text-primary", bad: "text-error",
  }[tone];
  return (
    <Card className="p-md">
      <div className="font-label-bold text-label-bold text-on-surface-variant uppercase">{label}</div>
      <div className={`font-headline-md text-headline-md mt-1 ${toneClass}`}>{value}</div>
      {sub && <div className="font-body-sm text-body-sm text-on-surface-variant mt-1">{sub}</div>}
    </Card>
  );
}

export function Badge({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-label-bold text-label-bold uppercase ${className}`}>
      {children}
    </span>
  );
}

export function ConfidenceBadge({ confidence, roc, std }: {
  confidence: Confidence; roc?: number; std?: number;
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <Badge className={confidenceStyle[confidence]}>{confidence} confidence</Badge>
      {roc !== undefined && (
        <span className="font-body-sm text-body-sm text-on-surface-variant mono">
          ROC-AUC {roc.toFixed(3)}{std !== undefined ? ` ± ${std.toFixed(3)}` : ""}
        </span>
      )}
    </span>
  );
}

export function TierBadge({ tier }: { tier: StructureTier }) {
  return <Badge className={tierStyle[tier]}>{tierLabel[tier]}</Badge>;
}

export function Seq({ children, className = "" }: { children: string; className?: string }) {
  return <span className={`mono font-code-md text-code-md break-all ${className}`}>{children}</span>;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-on-surface-variant">
      <span className="inline-block w-4 h-4 border-2 border-outline-variant border-t-primary rounded-full animate-spin" />
      <span className="font-body-md text-body-md">{label ?? "Working…"}</span>
    </div>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <div className="bg-error-container text-on-error-container border border-error/30 rounded-lg p-md flex items-start gap-2">
      <Icon name="error" size={18} />
      <div className="font-body-md text-body-md">{children}</div>
    </div>
  );
}

/** Used wherever a screen has no real data source yet. Never fake a number. */
export function Placeholder({ what }: { what: string }) {
  return (
    <div className="border border-dashed border-outline-variant rounded-lg p-lg text-center">
      <Icon name="pending" className="text-outline" />
      <div className="font-body-md text-body-md text-on-surface-variant mt-1">{what}</div>
      <div className="font-body-sm text-body-sm text-outline mt-1">
        No data source wired yet — shown empty rather than filled with a placeholder value.
      </div>
    </div>
  );
}

export function Button({ children, onClick, variant = "filled", disabled, className = "" }: {
  children: ReactNode; onClick?: () => void;
  variant?: "filled" | "outlined" | "text"; disabled?: boolean; className?: string;
}) {
  const base = "px-4 py-1.5 rounded font-label-bold text-label-bold inline-flex items-center gap-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed";
  const styles = {
    filled: "bg-primary text-on-primary hover:bg-primary-container",
    outlined: "border border-outline text-primary hover:bg-surface-container",
    text: "text-primary hover:bg-surface-container",
  }[variant];
  return (
    <button className={`${base} ${styles} ${className}`} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

/** Horizontal 0-1 meter. Presentation only. */
export function Meter({ value, tone = "primary" }: { value: number; tone?: "primary" | "error" | "secondary" }) {
  const bg = { primary: "bg-primary", error: "bg-error", secondary: "bg-secondary" }[tone];
  return (
    <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
      <div className={`h-full ${bg} rounded-full`} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </div>
  );
}
