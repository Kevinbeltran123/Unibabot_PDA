"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { FileText, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AssistantMessage, UserMessage } from "@/components/chat-message";
import { ProgressTimeline } from "@/components/progress-stream";
import { useAnalysis } from "@/hooks/use-analyses";
import { useProgressStream } from "@/hooks/use-progress-stream";
import { useAuth } from "@/hooks/use-auth";

export default function ProcessingPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;
  const { user } = useAuth();

  const { data: analysis } = useAnalysis(id, { refetchInterval: 3000 });
  const { events, status } = useProgressStream(id);

  React.useEffect(() => {
    if (!analysis) return;
    if (analysis.status === "done") {
      router.replace(`/dashboard/analyses/${id}`);
    }
  }, [analysis, id, router]);

  return (
    <div className="mx-auto w-full max-w-[760px] px-6 py-8">
      <UserMessage email={user?.email}>
        <UserPDARequest filename={analysis?.filename} />
      </UserMessage>

      <AssistantMessage>
        {analysis?.status === "failed" ? (
          <FailedState
            error={analysis.error}
            onRetry={() => router.push("/dashboard")}
          />
        ) : (
          <ProgressTimeline events={events} status={status} />
        )}
      </AssistantMessage>
    </div>
  );
}

function UserPDARequest({ filename }: { filename?: string }) {
  if (!filename) return null;
  return (
    <div className="inline-flex items-center gap-2">
      <FileText className="h-4 w-4 text-muted-foreground shrink-0" strokeWidth={1.75} />
      <span className="text-sm text-foreground truncate max-w-[320px]">{filename}</span>
    </div>
  );
}

function FailedState({
  error,
  onRetry,
}: {
  error: string | null | undefined;
  onRetry: () => void;
}) {
  return (
    <div className="space-y-3 max-w-prose">
      <p className="text-sm text-destructive leading-relaxed">
        El análisis no pudo completarse.
      </p>
      {error && (
        <pre className="text-xs text-foreground/80 bg-paper-warm border border-border rounded-md p-3 overflow-x-auto whitespace-pre-wrap">
          {error}
        </pre>
      )}
      <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5 mt-2">
        <RotateCw className="h-3.5 w-3.5" />
        Intentar con otro PDF
      </Button>
    </div>
  );
}
