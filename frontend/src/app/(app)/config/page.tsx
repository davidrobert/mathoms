"use client";

import { PageHeader } from "@/components/PageHeader";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import MembersTab from "./MembersTab";
import AcessosTab from "./AcessosTab";
import CategoriesTab from "./CategoriesTab";
import PipelineTab from "./PipelineTab";
import InstitutionsTab from "./InstitutionsTab";
import ReportLayoutTab from "./ReportLayoutTab";
import ImportExportTab from "./ImportExportTab";
import LLMTab from "./LLMTab";

const TABS = [
  { id: "members", label: "Membros" },
  { id: "acessos", label: "Acessos" },
  { id: "categories", label: "Categorias" },
  { id: "pipeline", label: "Pipeline" },
  { id: "llm", label: "LLM" },
  { id: "institutions", label: "Instituições" },
  { id: "layout", label: "Layout" },
  { id: "importexport", label: "Import/Export" },
] as const;

export default function ConfigPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Configurações"
        description="Membros do relatório, quem tem acesso ao app (Acessos), categorias, pipeline e layout"
      />

      <Tabs defaultValue="members">
        <TabsList className="mb-6 w-full justify-start">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="members"><MembersTab /></TabsContent>
        <TabsContent value="acessos"><AcessosTab /></TabsContent>
        <TabsContent value="categories"><CategoriesTab /></TabsContent>
        <TabsContent value="pipeline"><PipelineTab /></TabsContent>
        <TabsContent value="llm"><LLMTab /></TabsContent>
        <TabsContent value="institutions"><InstitutionsTab /></TabsContent>
        <TabsContent value="layout"><ReportLayoutTab /></TabsContent>
        <TabsContent value="importexport"><ImportExportTab /></TabsContent>
      </Tabs>
    </div>
  );
}
