"use client";

import { PageHeader } from "@/components/PageHeader";
import TransferConfigEditor from "./TransferConfigEditor";

export default function TransferConfigPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Transferências internas"
        description="Configure os nomes de pessoas e contas próprias da família para que transferências entre elas não apareçam como gastos."
      />
      <TransferConfigEditor />
    </div>
  );
}
