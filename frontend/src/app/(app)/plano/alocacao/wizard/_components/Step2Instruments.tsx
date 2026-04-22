"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Step2InstrumentsProps {
  instrumentosRf: string;
  instrumentosRv: string;
  onChangeRf: (v: string) => void;
  onChangeRv: (v: string) => void;
}

export function Step2Instruments({
  instrumentosRf,
  instrumentosRv,
  onChangeRf,
  onChangeRv,
}: Step2InstrumentsProps) {
  return (
    <div>
      <h2 className="text-lg font-semibold">Instrumentos preferidos</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Quais produtos voce prefere em cada classe? Opcional.
      </p>

      <div className="mt-6 space-y-4">
        <div>
          <Label htmlFor="rf-inst">Renda fixa</Label>
          <Input
            id="rf-inst"
            type="text"
            placeholder="Ex: Tesouro IPCA+, CDB, LCI"
            value={instrumentosRf}
            onChange={(e) => onChangeRf(e.target.value)}
            className="mt-2"
          />
        </div>
        <div>
          <Label htmlFor="rv-inst">Renda variavel</Label>
          <Input
            id="rv-inst"
            type="text"
            placeholder="Ex: ETFs, FIIs, IVVB11"
            value={instrumentosRv}
            onChange={(e) => onChangeRv(e.target.value)}
            className="mt-2"
          />
        </div>
      </div>
    </div>
  );
}
