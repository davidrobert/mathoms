"use client";

import { cn } from "@/lib/cn";
import { Input } from "@/components/ui/input";

interface DateRangePickerProps {
  from: string | null;
  to: string | null;
  onChange: (from: string | null, to: string | null) => void;
  className?: string;
}

export function DateRangePicker({
  from,
  to,
  onChange,
  className,
}: DateRangePickerProps) {
  return (
    <div className={cn("flex flex-row items-center gap-2", className)}>
      <label className="text-sm text-muted-foreground whitespace-nowrap">
        De
      </label>
      <Input
        type="date"
        value={from ?? ""}
        onChange={(e) => onChange(e.target.value || null, to)}
        className="w-36"
      />
      <label className="text-sm text-muted-foreground whitespace-nowrap">
        Até
      </label>
      <Input
        type="date"
        value={to ?? ""}
        onChange={(e) => onChange(from, e.target.value || null)}
        className="w-36"
      />
    </div>
  );
}
