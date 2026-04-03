export type ModelId = 'opus' | 'sonnet' | 'haiku'

export interface ModelPricing {
  id: ModelId
  name: string
  inputPer1M: number
  outputPer1M: number
  cacheHitPer1M: number
  contextWindow: string
}

export const MODELS: Record<ModelId, ModelPricing> = {
  opus: {
    id: 'opus',
    name: 'Opus 4.6',
    inputPer1M: 5.0,
    outputPer1M: 25.0,
    cacheHitPer1M: 0.5,
    contextWindow: '1M',
  },
  sonnet: {
    id: 'sonnet',
    name: 'Sonnet 4.6',
    inputPer1M: 3.0,
    outputPer1M: 15.0,
    cacheHitPer1M: 0.3,
    contextWindow: '1M',
  },
  haiku: {
    id: 'haiku',
    name: 'Haiku 4.5',
    inputPer1M: 1.0,
    outputPer1M: 5.0,
    cacheHitPer1M: 0.1,
    contextWindow: '200K',
  },
}

export const FAST_MODE_MULTIPLIER = 6

export const TOKEN_ESTIMATES = {
  tokensPerClaudeMdLine: 7,
  systemPromptTokens: 3500,
  tokensPerMcpServer: 1500,
  tokensPerFileRead: 2000,
  outputTokensPerTurn: 500,
  historyGrowthPerTurn: 1500,
  cacheHitRate: 0.7,
}

export function formatDollars(amount: number): string {
  return `$${amount.toFixed(2)}`
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`
}
