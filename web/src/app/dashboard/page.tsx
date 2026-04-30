"use client";

import * as React from "react";
import { ChatComposer } from "@/components/chat-composer";
import { AssistantMessage, UserMessage } from "@/components/chat-message";
import { RejectionMessage } from "@/components/chat-rejection";
import { useAnalyses } from "@/hooks/use-analyses";
import { useAuth } from "@/hooks/use-auth";

/*
 * Home del dashboard como conversación tipo chat.
 *
 * Estado: una lista local de mensajes UI-only (no persistente). Cada vez
 * que el usuario sube un PDF, se añade un UserMessage y luego —si el
 * backend rechaza con 422— un AssistantMessage de rechazo con el mensaje
 * natural y un hint dependiente del código. Los uploads exitosos navegan
 * a /processing; los errores no-422 siguen como toast en el composer.
 */

interface UiMessage {
  id: string;
  kind: "user-upload" | "assistant-rejection";
  filename: string;
  rejection?: { message: string; code?: string };
}

export default function DashboardPage() {
  const { data, isLoading } = useAnalyses();
  const { user } = useAuth();
  const hasHistory = !isLoading && data && data.length > 0;
  const [messages, setMessages] = React.useState<UiMessage[]>([]);
  const composerRef = React.useRef<HTMLDivElement | null>(null);

  const handleSubmitStart = React.useCallback((filename: string) => {
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, kind: "user-upload", filename },
    ]);
  }, []);

  const handleRejection = React.useCallback(
    (params: { filename: string; message: string; code?: string }) => {
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          kind: "assistant-rejection",
          filename: params.filename,
          rejection: { message: params.message, code: params.code },
        },
      ]);
    },
    [],
  );

  const handleRetry = React.useCallback(() => {
    composerRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, []);

  return (
    <div className="mx-auto w-full max-w-[720px] px-6 py-10 sm:py-16 flex flex-col min-h-full">
      <div className="flex-1 flex flex-col">
        <AssistantMessage withDivider={false}>
          {hasHistory || messages.length > 0 ? (
            <ContinuationGreeting />
          ) : (
            <FirstTimeGreeting />
          )}
        </AssistantMessage>

        {messages.map((m) => {
          if (m.kind === "user-upload") {
            return (
              <UserMessage key={m.id} email={user?.email}>
                <span className="text-sm">Subí: {m.filename}</span>
              </UserMessage>
            );
          }
          return (
            <AssistantMessage key={m.id}>
              <RejectionMessage
                filename={m.filename}
                message={m.rejection?.message ?? ""}
                code={m.rejection?.code}
                onRetry={handleRetry}
              />
            </AssistantMessage>
          );
        })}
      </div>

      <div ref={composerRef} className="mt-12 pb-4">
        <ChatComposer
          onSubmitStart={handleSubmitStart}
          onRejection={handleRejection}
        />
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
