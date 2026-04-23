"use client";

import type { ButtonHTMLAttributes, InputHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const VARIANT_CLASS: Record<Variant, string> = {
  primary: "bg-brand-primary text-brand-primary-fg hover:opacity-90",
  secondary: "bg-surface-muted text-surface-fg hover:bg-surface-border",
  danger: "bg-brand-danger text-brand-danger-fg hover:opacity-90",
  ghost: "bg-transparent text-surface-fg hover:bg-surface-muted",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({
  variant = "primary",
  className = "",
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      className={`px-3 py-1.5 rounded-md text-sm font-medium disabled:opacity-50 ${VARIANT_CLASS[variant]} ${className}`}
    />
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  const { className = "", ...rest } = props;
  return (
    <input
      {...rest}
      className={`rounded-md border border-surface-border bg-surface-bg px-3 py-2 text-sm text-surface-fg focus:outline-none focus:ring-2 focus:ring-brand-primary ${className}`}
    />
  );
}

interface BadgeProps {
  tone?: "neutral" | "success" | "warning" | "danger";
  children: React.ReactNode;
}

const BADGE_CLASS: Record<NonNullable<BadgeProps["tone"]>, string> = {
  neutral: "bg-surface-muted text-surface-muted-fg",
  success: "bg-semantic-gain/15 text-semantic-gain",
  warning: "bg-semantic-alert/20 text-brand-warning-fg",
  danger: "bg-brand-danger/15 text-brand-danger",
};

export function Badge({ tone = "neutral", children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-pill px-2 py-0.5 text-xs font-medium ${BADGE_CLASS[tone]}`}
    >
      {children}
    </span>
  );
}
