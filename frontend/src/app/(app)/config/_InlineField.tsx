"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Check, X } from "lucide-react";

export function InlineField({
  label,
  value,
  onSave,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onSave: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(value);
  if (!editing) {
    return (
      <div>
        <Label className="mb-1 text-xs text-muted-foreground">{label}</Label>
        <button
          onClick={() => setEditing(true)}
          className="w-full text-left rounded-lg border border-transparent px-2 py-1.5 text-sm hover:border-border hover:bg-accent"
        >
          {value || <span className="text-muted-foreground">{placeholder ?? "—"}</span>}
        </button>
      </div>
    );
  }

  return (
    <div>
      <Label className="mb-1 text-xs text-muted-foreground">{label}</Label>
      <div className="flex gap-1">
        <Input
          type={type}
          value={val}
          onChange={(e) => setVal(e.target.value)}
          placeholder={placeholder}
          autoFocus
          className="flex-1"
        />
        <Button size="sm" onClick={() => { onSave(val); setEditing(false); }}>
          <Check className="h-3.5 w-3.5" />
        </Button>
        <Button size="sm" variant="outline" onClick={() => { setVal(value); setEditing(false); }}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
