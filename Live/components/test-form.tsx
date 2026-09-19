"use client"

import type React from "react"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Play, Loader2 } from "lucide-react"

export function TestForm({ onRun }: { onRun: (goal: string, url: string) => void }) {
  const [goal, setGoal] = useState("Add a laptop to the cart and reach the checkout page")
  const [url, setUrl] = useState("https://demo.target-app.dev")
  const [running, setRunning] = useState(false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (running) return
    setRunning(true)
    // Simulate an agent run; no backend calls yet.
    window.setTimeout(() => {
      onRun(goal, url)
      setRunning(false)
    }, 900)
  }

  return (
    <Card>
      <CardContent className="p-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="goal">Test goal</Label>
              <Input
                id="goal"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="e.g. Sign up for a new account"
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="url">Target URL</Label>
              <Input
                id="url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com"
                required
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button type="submit" disabled={running} className="gap-2">
              {running ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Running…
                </>
              ) : (
                <>
                  <Play className="size-4" />
                  Run Test
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
