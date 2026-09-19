import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { Finding } from "@/lib/types"

const severityStyles: Record<Finding["severity"], string> = {
  Critical: "bg-red-600 text-white hover:bg-red-600",
  Moderate: "bg-amber-500 text-white hover:bg-amber-500",
  Minor: "bg-slate-400 text-white hover:bg-slate-400",
}

export function FindingsList({
  title,
  items,
  tone,
  emptyLabel,
}: {
  title: string
  items: Finding[]
  tone: "friction" | "accessibility"
  emptyLabel: string
}) {
  const dotClass = tone === "friction" ? "bg-amber-500" : "bg-violet-500"

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {title} ({items.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{emptyLabel}</p>
        ) : (
          <ul className="space-y-3">
            {items.map((item, i) => (
              <li key={i} className="flex flex-col gap-1.5 text-sm">
                <div className="flex items-start gap-3">
                  <span className={`mt-1.5 size-2 shrink-0 rounded-full ${dotClass}`} />
                  <span className="text-pretty leading-relaxed">{item.text}</span>
                </div>
                <div className="flex items-center gap-2 pl-5">
                  <Badge className={`text-xs ${severityStyles[item.severity]}`}>
                    {item.severity}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {item.confidence}% confidence
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
