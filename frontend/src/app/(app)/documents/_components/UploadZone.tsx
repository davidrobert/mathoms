"use client";

import { useState } from "react";
import { Upload } from "lucide-react";
import { Card } from "@/components/ui/card";

interface UploadZoneProps {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  uploading: boolean;
  uploadProgress: number;
  onSelect: (files: FileList | File[]) => void;
}

function UploadingBar({ progress }: { progress: number }) {
  return (
    <div>
      <div className="mx-auto mb-3 h-2 w-64 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="text-sm text-muted-foreground">Enviando... {progress}%</p>
    </div>
  );
}

function UploadPrompt() {
  return (
    <>
      <Upload className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
      <p className="text-sm font-medium">
        Arraste arquivos aqui ou clique para selecionar
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        PDF, CSV, XLSX, JPG, PNG, JSON — até 20 arquivos, 50MB cada
      </p>
    </>
  );
}

export function UploadZone({
  fileInputRef,
  uploading,
  uploadProgress,
  onSelect,
}: UploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) onSelect(e.dataTransfer.files);
  };

  const dragClass = dragOver ? "border-primary bg-primary/5" : "border-border hover:border-muted-foreground";

  return (
    <Card
      className={`mb-6 cursor-pointer border-2 border-dashed p-8 text-center transition ${dragClass} ${
        uploading ? "pointer-events-none opacity-60" : ""
      }`}
      onDragOver={(e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.csv,.xlsx,.xls,.jpg,.jpeg,.png,.json"
        className="hidden"
        aria-label="Selecionar arquivos para upload"
        onChange={(e) => e.target.files && onSelect(e.target.files)}
      />
      {uploading ? <UploadingBar progress={uploadProgress} /> : <UploadPrompt />}
    </Card>
  );
}
