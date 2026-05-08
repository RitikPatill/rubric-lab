export type RubricDimension = {
  id: string
  name: string
  description: string
  weight: number
}

export type Case = {
  id: string
  suiteId: string
  title: string
  input: string
  context?: string
  expectedBehavior: string
  rubric: RubricDimension[]
  createdAt: string
}

export type Suite = {
  id: string
  name: string
  description: string
  createdAt: string
  cases?: Case[]
}

export type Trace = {
  id: string
  caseResultId: string
  events: TraceEvent[]
  latencyMs: number
  inputTokens: number
  outputTokens: number
}

export type TraceEvent = {
  type: 'message' | 'tool_call' | 'tool_result'
  timestamp: string
  content: string
}

export type RubricScore = {
  id: string
  caseResultId: string
  dimensionId: string
  dimensionName: string
  score: number
  justification: string
}

export type CaseResult = {
  id: string
  runId: string
  caseId: string
  passed: boolean
  scores: RubricScore[]
  trace: Trace
}

export type Run = {
  id: string
  suiteId: string
  status: 'pending' | 'running' | 'done' | 'failed'
  createdAt: string
  results: CaseResult[]
}
