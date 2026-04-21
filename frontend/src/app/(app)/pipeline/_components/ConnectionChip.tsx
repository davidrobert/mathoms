"use client";

import { Wifi, WifiOff } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function ConnectedChip() {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span className="inline-flex items-center gap-1 rounded-full bg-gain/10 px-2 py-0.5 text-[10px] font-medium text-gain cursor-default" />
        }
      >
        <Wifi className="h-2.5 w-2.5" />
        Tempo real
      </TooltipTrigger>
      <TooltipContent>Conectado via WebSocket — atualizações instantâneas</TooltipContent>
    </Tooltip>
  );
}

function ConnectingChip() {
  return (
    <span className="inline-flex animate-pulse items-center gap-1 rounded-full bg-alert/10 px-2 py-0.5 text-[10px] font-medium text-alert">
      <Wifi className="h-2.5 w-2.5" />
      Conectando...
    </span>
  );
}

function PollingChip() {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground cursor-default" />
        }
      >
        <WifiOff className="h-2.5 w-2.5" />
        Polling
      </TooltipTrigger>
      <TooltipContent>Sem conexão em tempo real — atualizando a cada 2s</TooltipContent>
    </Tooltip>
  );
}

export function ConnectionChip({ status }: { status: string }) {
  if (status === "connected") return <ConnectedChip />;
  if (status === "connecting") return <ConnectingChip />;
  return <PollingChip />;
}
