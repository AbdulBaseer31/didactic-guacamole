export interface Finding {
  text: string
  severity: "Critical" | "Moderate" | "Minor"
  confidence: number // 0-100
}

export interface Action {
  step: number
  description: string
  success: boolean
  evidence: string[]
}

export interface AlternatePath {
  steps: number
  outcome: string
}

export interface RunResult {
  goal: string
  steps: number
  visited: string[]
  actions: Action[]
  friction: Finding[]
  accessibility_issues: Finding[]
  goal_achieved: boolean | null
  alternate_path: AlternatePath | null
}
