import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { RunResult } from "@/lib/types"
import { CheckCircle2, XCircle, HelpCircle, Footprints, AlertTriangle, Accessibility } from "lucide-react"

function GoalBadge({ achieved }: { achieved: boolean | null }) {
  if (achieved === true) {
    return (
      <Badge className="gap-1 bg-emerald-600 text-white hover:bg-emerald-600">
        <CheckCircle2 className="size-3.5" />
        Goal achieved
      </Badge>
    )
  }
  if (achieved === false) {
    return (
      <Badge variant="destructive" className="gap-1">
        <XCircle className="size-3.5" />
        Goal not achieved
      </Badge>
    )
  }
  return (
    <Badge variant="secondary" className="gap-1">
      <HelpCircle className="size-3.5" />
      Inconclusive
    </Badge>
  )
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: number | string
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        {icon}
      </div>
      <div>
        <div className="text-2xl font-semibold leading-none tabular-nums">{value}</div>
        <div className="mt-1 text-xs text-muted-foreground">{label}</div>
      </div>
    </div>
  )
}

export function SummaryCard({ result }: { result: RunResult }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Goal</p>
            <h2 className="mt-1 text-pretty text-lg font-semibold leading-snug">{result.goal}</h2>
          </div>
          <GoalBadge achieved={result.goal_achieved} />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Stat icon={<Footprints className="size-5" />} label="Steps taken" value={result.steps} />
          <Stat
            icon={<AlertTriangle className="size-5" />}
            label="Friction findings"
            value={result.friction.length}
          />
          <Stat
            icon={<Accessibility className="size-5" />}
            label="Accessibility issues"
            value={result.accessibility_issues.length}
          />
        </div>
      </CardContent>
    </Card>
  )
}
