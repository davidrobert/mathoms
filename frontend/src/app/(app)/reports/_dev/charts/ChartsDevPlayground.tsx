"use client";

import { useState } from "react";
import {
  ChartBar,
  ChartStackedBar,
  ChartDonut,
  ChartPie,
  ChartLine,
  ChartCombo,
  ChartWaterfall,
  ChartGaugeSemi,
  ChartGaugeScore,
  ChartConclusion,
  ChartNav,
} from "@/components/report/charts/primitives";

const MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"];

export function ChartsDevPlayground() {
  const [navPage, setNavPage] = useState(0);

  return (
    <div
      data-report-scope
      data-font-scale="compact"
      style={{
        padding: 32,
        display: "flex",
        flexDirection: "column",
        gap: 48,
        maxWidth: 960,
        margin: "0 auto",
      }}
    >
      <header>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 800 }}>
          Chart primitives — playground
        </h1>
        <p style={{ color: "var(--surface-muted-foreground)", marginTop: 4 }}>
          DEV only. Renderiza cada primitivo com fixtures. Troque o tema via toggle global.
        </p>
      </header>

      <section>
        <h2>ChartBar</h2>
        <div style={{ height: 300 }}>
          <ChartBar
            labels={[...MONTHS]}
            series={[
              { label: "Receita", data: [12000, 15000, 14000, 17000, 16000, 18000] },
              { label: "Despesa", data: [9000, 11000, 10500, 12000, 11500, 13000] },
            ]}
            height={280}
          />
        </div>
        <ChartConclusion>
          Receita cresceu 50% no semestre; despesas acompanham o movimento em menor intensidade.
        </ChartConclusion>
      </section>

      <section>
        <h2>ChartStackedBar</h2>
        <div style={{ height: 300 }}>
          <ChartStackedBar
            labels={[...MONTHS]}
            series={[
              { label: "Essencial", data: [5000, 5200, 5100, 5400, 5300, 5600] },
              { label: "Variável", data: [3000, 3500, 3200, 4000, 3800, 4200] },
              { label: "Extraordinário", data: [1000, 2300, 2200, 2600, 2400, 3200] },
            ]}
            height={280}
          />
        </div>
      </section>

      <section>
        <h2>ChartDonut + ChartPie</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <div style={{ height: 300 }}>
            <ChartDonut
              data={[
                { label: "Renda Fixa", value: 340000 },
                { label: "Renda Variável", value: 180000 },
                { label: "Imóveis", value: 520000 },
                { label: "Caixa", value: 60000 },
              ]}
              centerLabel="Patrimônio"
              centerValue="R$ 1,1 mi"
              showDataLabels
            />
          </div>
          <div style={{ height: 300 }}>
            <ChartPie
              data={[
                { label: "Alimentação", value: 2400 },
                { label: "Transporte", value: 1200 },
                { label: "Moradia", value: 3800 },
                { label: "Lazer", value: 900 },
              ]}
            />
          </div>
        </div>
      </section>

      <section>
        <h2>ChartLine</h2>
        <div style={{ height: 300 }}>
          <ChartLine
            labels={[...MONTHS]}
            series={[
              { label: "Patrimônio líquido", data: [900000, 920000, 935000, 970000, 990000, 1_010_000] },
            ]}
            filled
            height={280}
          />
        </div>
      </section>

      <section>
        <h2>ChartCombo (bar + line)</h2>
        <div style={{ height: 300 }}>
          <ChartCombo
            labels={[...MONTHS]}
            series={[
              { kind: "bar", label: "Aportes", data: [3000, 3500, 4000, 3800, 4200, 4500] },
              { kind: "line", label: "Saldo acumulado", data: [3000, 6500, 10500, 14300, 18500, 23000] },
            ]}
            height={280}
          />
        </div>
      </section>

      <section>
        <h2>ChartWaterfall</h2>
        <div style={{ height: 320 }}>
          <ChartWaterfall
            steps={[
              { label: "Saldo inicial", value: 50000, kind: "start" },
              { label: "Receitas", value: 18000 },
              { label: "Despesas", value: -12000 },
              { label: "Investimentos", value: -4000 },
              { label: "Saldo final", value: 52000, kind: "end" },
            ]}
            height={300}
          />
        </div>
      </section>

      <section>
        <h2>ChartGaugeSemi</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 24 }}>
          <ChartGaugeSemi value={2.8} max={10} centerValue="2.8" centerLabel="Crítico" />
          <ChartGaugeSemi value={5.5} max={10} centerValue="5.5" centerLabel="Regular" />
          <ChartGaugeSemi value={8.9} max={10} centerValue="8.9" centerLabel="Excelente" />
        </div>
      </section>

      <section>
        <h2>ChartGaugeScore (Score Financeiro — paridade com EXEMPLO_DE_RELATORIO.html)</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <ChartGaugeScore value={1.4} max={10} classeLabel="PÉSSIMO" classeKey="pessimo" />
          <ChartGaugeScore value={3.2} max={10} classeLabel="RUIM" classeKey="ruim" />
          <ChartGaugeScore value={5.5} max={10} classeLabel="REGULAR" classeKey="regular" />
          <ChartGaugeScore value={6.9} max={10} classeLabel="BOM" classeKey="bom" />
          <ChartGaugeScore value={8.7} max={10} classeLabel="EXCELENTE" classeKey="excelente" />
        </div>
      </section>

      <section>
        <h2>ChartNav</h2>
        <ChartNav
          label={`Janeiro a Junho · Página ${navPage + 1}/4`}
          page={navPage}
          total={4}
          onPrev={() => setNavPage((p) => Math.max(0, p - 1))}
          onNext={() => setNavPage((p) => Math.min(3, p + 1))}
        />
      </section>
    </div>
  );
}
