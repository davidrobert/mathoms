"use client";

import Link from "next/link";
import { ArrowRight, Target } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function EmptyGoalsBanner() {
  return (
    <Card className="mb-6 border-dashed">
      <CardContent className="py-8">
        <div className="mx-auto max-w-lg text-center">
          <Target className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
          <h2 className="text-lg font-semibold">
            Configure suas metas financeiras
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Configure suas metas financeiras para gerar relatorios completos e
            acompanhar seu progresso.
          </p>
          <Button
            nativeButton={false}
            render={<Link href="/plano/meta-if/wizard" />}
            className="mt-6"
          >
            Comecar <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
