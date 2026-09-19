"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { Action } from "@/lib/types"
import { CheckCircle2, XCircle, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

function ActionRow({ action }: { action: Action }) {
  const [open, setOpen] = useState(false)
  const panelId = `action-evidence-${action.step}`

  return (
    <li className="overflow-hidden rounded-lg border">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/60"
      >
        <ChevronRight className={cn("size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-90")} />
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium tabular-nums">
          {action.step}
        </span>
        <span className="min-w-0 flex-1 text-sm font-medium">{action.description}</span>
        {action.success ? (
          <Badge className="gap-1 bg-emerald-600 text-white hover:bg-emerald-600">
            <CheckCircle2 className="size-3.5" />
            Success
          </Badge>
        ) : (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="size-3.5" />
            Failed
          </Badge>
        )}
      </button>

      {open && (
        <div id={panelId} className="border-t bg-muted/30 px-4 py-3">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Evidence</p>
          <ul className="space-y-1.5">
            {action.evidence.map((item, i) => (
              <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-muted-foreground/50" />
                <span className="text-pretty">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  )
}

export function ActionList({ actions }: { actions: Action[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Actions ({actions.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {actions.map((action) => (
            <ActionRow key={action.step} action={action} />
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
