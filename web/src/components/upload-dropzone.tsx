"use client";

import * as React from "react";
import { useDropzone } from "react-dropzone";
import { FileText, Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  onFileSelected: (file: File) => void;
  selectedFile: File | null;
}

export function UploadDropzone({ onFileSelected, selectedFile }: Props) {
  const onDrop = React.useCallback(
    (accepted: File[]) => {
      if (accepted[0]) onFileSelected(accepted[0]);
    },
    [onFileSelected],
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    multiple: false,
    accept: { "application/pdf": [".pdf"] },
    maxSize: 20 * 1024 * 1024,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed bg-card px-6 py-12 text-center transition-all cursor-pointer hover:border-primary/50 hover:bg-accent/30",
        isDragActive && "border-primary bg-primary/5 scale-[1.01]",
        isDragReject && "border-destructive bg-destructive/5",
        selectedFile && "border-primary/30 bg-primary/[0.02]",
      )}
    >
      <input {...getInputProps()} aria-label="Subir PDF" />
      {selectedFile ? (
        <div className="flex flex-col items-center gap-2">
          <FileText className="h-10 w-10 text-primary" />
          <div className="font-medium">{selectedFile.name}</div>
          <div className="text-xs text-muted-foreground">
            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB · click para cambiar
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Upload className="h-6 w-6 text-primary" />
          </div>
          <div>
            <div className="font-medium">
              {isDragActive ? "Suelta el PDF aqui" : "Arrastra un PDF o haz click para seleccionar"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">PDF hasta 20 MB</div>
          </div>
        </div>
      )}
    </div>
  );
}
