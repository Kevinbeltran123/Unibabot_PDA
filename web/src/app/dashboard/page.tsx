"use client";

import * as React from "react";
import { ChatComposer } from "@/components/chat-composer";
import { AssistantMessage } from "@/components/chat-message";
import { useAnalyses } from "@/hooks/use-analyses";

/*
 * Home del dashboard. Contiene un mensaje de bienvenida del asistente
 * (estilo serif editorial) seguido del composer. Cuando ya hay analisis
 * pasados, el mensaje se acorta para no repetirse cada visita.
 */

export default function DashboardPage() {
  const { data, isLoading } = useAnalyses();
  const hasHistory = !isLoading && data && data.length > 0;

  return (
    <div className="mx-auto w-full max-w-[720px] px-6 py-10 sm:py-16 flex flex-col min-h-full">
      <div className="flex-1 flex flex-col justify-center">
        <AssistantMessage withDivider={false}>
          {hasHistory ? (
            <ContinuationGreeting />
          ) : (
            <FirstTimeGreeting />
          )}
        </AssistantMessage>
      </div>

      {/* Composer area */}
      <div className="mt-12 pb-4">
        <ChatComposer />
      </div>
    </div>
  );
}

function FirstTimeGreeting() {
  return (
    <div className="space-y-4">
      <h1 className="text-[1.875rem] font-medium leading-[1.15] text-foreground tracking-tight">
        Bienvenido.
      </h1>
      <p className="text-base leading-relaxed text-foreground/85 max-w-prose">
        Soy el agente que verifica que un Plan de Desarrollo Académico cumpla con los
        179 lineamientos institucionales. Adjunta un PDA en formato PDF y te entrego
        un reporte estructurado con cada hallazgo, evidencia citada y sugerencias de
        corrección para los puntos que no cumplen.
      </p>
      <p className="text-sm leading-relaxed text-muted-foreground max-w-prose">
        Aún no has analizado ningún PDA. Adjunta tu primer documento desde el campo de
        abajo para empezar.
      </p>
    </div>
  );
}

function ContinuationGreeting() {
  return (
    <h1 className="text-[1.5rem] font-medium leading-tight text-foreground tracking-tight">
      ¿Qué PDA quieres analizar hoy?
    </h1>
  );
}
