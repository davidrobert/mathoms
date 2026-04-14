"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Sun, Moon, Monitor } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const CYCLE: Record<string, string> = {
  light: "dark",
  dark: "system",
  system: "light",
};

const LABELS: Record<string, string> = {
  light: "Claro",
  dark: "Escuro",
  system: "Sistema",
};

const ICONS: Record<string, typeof Sun> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
};

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className="h-8 w-8" disabled>
        <Monitor className="h-4 w-4" />
      </Button>
    );
  }

  const current = theme ?? "system";
  const Icon = ICONS[current] ?? Monitor;
  const next = CYCLE[current] ?? "light";

  return (
    <TooltipProvider delay={300}>
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setTheme(next)}
              aria-label={`Tema: ${LABELS[current]}. Clique para ${LABELS[next]}`}
            />
          }
        >
          <Icon className="h-4 w-4" />
        </TooltipTrigger>
        <TooltipContent side="top">
          <p>Tema: {LABELS[current]}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
