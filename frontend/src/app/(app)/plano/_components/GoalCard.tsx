"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export interface GoalCardProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  configured: boolean;
  href: string;
  value?: string;
  subtitle?: string;
}

export function GoalCard({
  icon: Icon,
  title,
  configured,
  href,
  value,
  subtitle,
}: GoalCardProps) {
  return (
    <Card className="transition-colors hover:border-border">
      <Link href={href} className="block">
        <CardContent className="flex items-start gap-4 py-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
            <Icon className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold">{title}</h3>
              {configured ? (
                <Badge variant="outline" className="text-xs">
                  Configurada
                </Badge>
              ) : (
                <Badge variant="secondary" className="text-xs">
                  Pendente
                </Badge>
              )}
            </div>
            {configured && value ? (
              <>
                <p className="mt-1 font-mono text-sm tabular-nums font-medium">
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
          <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
        </CardContent>
      </Link>
    </Card>
  );
}
