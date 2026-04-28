"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/cn";

export interface GoalCardProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  configured: boolean;
  href: string;
  value?: string;
  subtitle?: string;
  density?: "default" | "compact";
}

export function GoalCard({
  icon,
  title,
  configured,
  href,
  value,
  subtitle,
  density = "default",
}: GoalCardProps) {
  const compact = density === "compact";
  return (
    <Card className="transition-colors hover:border-border">
      <Link href={href} className="block">
        <CardContent
          className={cn(
            "flex items-start",
            compact ? "py-3 gap-3" : "py-5 gap-4"
          )}
        >
          <GoalIcon icon={icon} compact={compact} />
          <GoalBody
            title={title}
            configured={configured}
            value={value}
            subtitle={subtitle}
            compact={compact}
          />
          <ArrowRight
            className={cn(
              "mt-1 shrink-0 text-muted-foreground",
              compact ? "h-3.5 w-3.5" : "h-4 w-4"
            )}
          />
        </CardContent>
      </Link>
    </Card>
  );
}

function GoalIcon({
  icon: Icon,
  compact,
}: {
  icon: GoalCardProps["icon"];
  compact: boolean;
}) {
  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-lg bg-muted",
        compact ? "h-8 w-8" : "h-10 w-10"
      )}
    >
      <Icon
        className={cn(
          "text-muted-foreground",
          compact ? "h-4 w-4" : "h-5 w-5"
        )}
      />
    </div>
  );
}

interface GoalBodyProps {
  title: string;
  configured: boolean;
  value?: string;
  subtitle?: string;
  compact: boolean;
}

function GoalBody({
  title,
  configured,
  value,
  subtitle,
  compact,
}: GoalBodyProps) {
  return (
    <div className="min-w-0 flex-1">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        {!configured && (
          <Badge variant="secondary" className="text-xs">
            Pendente
          </Badge>
        )}
        {configured && !compact && (
          <Badge variant="outline" className="text-xs">
            Configurada
          </Badge>
        )}
      </div>
      {configured && value ? (
        <>
          <p className="mt-1 font-mono text-sm font-medium tabular-nums">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </>
      ) : (
        <p className="mt-1 text-xs text-muted-foreground">
          Clique para configurar
        </p>
      )}
    </div>
  );
}
