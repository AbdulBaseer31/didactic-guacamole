"use client"

import { useState } from "react"
import { TestForm } from "@/components/test-form"
import { SummaryCard } from "@/components/summary-card"
import { ActionList } from "@/components/action-list"
import { FindingsList } from "@/components/findings-list"
import { sampleRunResult } from "@/lib/mock-data"
import type { RunResult } from "@/lib/types"
import { Bot, Globe } from "lucide-react"

export default function Page() {
  const [result, setResult] = useState<RunResult | null>(null)

  function handleRun(goal: string, url: string) {
    // Mock: return the hardcoded sample, overriding the goal with the user's input.
    setResult({ ...sampleRunResult, goal })
  }

  return (
    <main className="mx-auto min-h-screen w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
      <header className="mb-8">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Bot className="size-4" />
          Pragyaan
        </div>
        <h1 className="mt-2 text-balance text-2xl font-semibold tracking-tight sm:text-3xl">
          Agentic UX &amp; Accessibility Tester
        </h1>
        <p className="mt-2 max-w-2xl text-pretty text-sm text-muted-foreground">
          An AI agent navigates your app using only visible interactive elements, acts like a human tester, and reports
          UX friction and accessibility issues.
        </p>
      </header>

      <div className="space-y-6">
        <TestForm onRun={handleRun} />

        {result ? (
          <div className="space-y-6">
            <SummaryCard result={result} />

            <div className="grid gap-6 lg:grid-cols-5">
              <div className="lg:col-span-3">
                <ActionList actions={result.actions} />
              </div>
              <div className="space-y-6 lg:col-span-2">
                <FindingsList
                  title="Friction findings"
                  items={result.friction}
                  tone="friction"
                  emptyLabel="No friction detected."
                />
                <FindingsList
                  title="Accessibility issues"
                  items={result.accessibility_issues}
                  tone="accessibility"
                  emptyLabel="No accessibility issues detected."
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <Globe className="size-6" />
            </div>
            <p className="mt-4 text-sm font-medium">No results yet</p>
            <p className="mt-1 max-w-sm text-pretty text-sm text-muted-foreground">
              Enter a goal and target URL, then run a test to see the agent&apos;s actions and findings.
            </p>
          </div>
        )}
      </div>
    </main>
  )
}
