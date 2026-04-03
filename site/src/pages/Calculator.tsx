import { useState, useMemo, useCallback } from 'react'
import { type ModelId, MODELS, formatDollars } from '../utils/pricing'
import { calculate, resultToMarkdown, type CalculatorInputs } from '../utils/calculator'
import styles from './Calculator.module.css'

const defaultInputs: CalculatorInputs = {
  model: 'opus',
  turnsPerSession: 30,
  claudeMdLines: 100,
  sessionsPerDay: 3,
  workingDaysPerMonth: 22,
  mcpServers: 2,
  fileReadsPerTurn: 1,
  fastMode: false,
}

function Calculator() {
  const [inputs, setInputs] = useState<CalculatorInputs>(defaultInputs)
  const [copied, setCopied] = useState(false)

  const result = useMemo(() => calculate(inputs), [inputs])

  const updateField = useCallback(
    <K extends keyof CalculatorInputs>(field: K, value: CalculatorInputs[K]) => {
      setInputs((prev) => ({ ...prev, [field]: value }))
    },
    [],
  )

  const handleNumberChange = useCallback(
    (field: keyof CalculatorInputs) => (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = parseInt(e.target.value, 10)
      if (!isNaN(val) && val >= 0) {
        updateField(field, val as CalculatorInputs[typeof field])
      }
    },
    [updateField],
  )

  const handleCopy = useCallback(() => {
    const md = resultToMarkdown(inputs, result)
    navigator.clipboard.writeText(md).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [inputs, result])

  return (
    <div className={styles.calculator}>
      <h1 className={styles.title}>Cost Calculator</h1>
      <p className={styles.subtitle}>
        Estimate your monthly Claude Code costs and see where tokens go.
      </p>

      <div className={styles.grid}>
        <div className={styles.inputPanel}>
          <h2 className={styles.panelTitle}>Configuration</h2>

          <fieldset className={styles.fieldset}>
            <legend className={styles.legend}>Model</legend>
            <div className={styles.radioGroup}>
              {(Object.keys(MODELS) as ModelId[]).map((id) => (
                <label key={id} className={styles.radioLabel}>
                  <input
                    type="radio"
                    name="model"
                    value={id}
                    checked={inputs.model === id}
                    onChange={() => {
                      updateField('model', id)
                      if (id !== 'opus') updateField('fastMode', false)
                    }}
                    className={styles.radio}
                  />
                  <span className={styles.radioText}>
                    {MODELS[id].name}
                    <span className={styles.radioMeta}>
                      ${MODELS[id].inputPer1M}/${MODELS[id].outputPer1M} per 1M
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className={styles.inputGrid}>
            <label className={styles.inputLabel}>
              <span>Turns per session</span>
              <input
                type="number"
                min={1}
                max={200}
                value={inputs.turnsPerSession}
                onChange={handleNumberChange('turnsPerSession')}
                className={styles.numberInput}
              />
            </label>

            <label className={styles.inputLabel}>
              <span>CLAUDE.md lines</span>
              <input
                type="number"
                min={0}
                max={1000}
                value={inputs.claudeMdLines}
                onChange={handleNumberChange('claudeMdLines')}
                className={styles.numberInput}
              />
            </label>

            <label className={styles.inputLabel}>
              <span>Sessions per day</span>
              <input
                type="number"
                min={1}
                max={50}
                value={inputs.sessionsPerDay}
                onChange={handleNumberChange('sessionsPerDay')}
                className={styles.numberInput}
              />
            </label>

            <label className={styles.inputLabel}>
              <span>Working days / month</span>
              <input
                type="number"
                min={1}
                max={31}
                value={inputs.workingDaysPerMonth}
                onChange={handleNumberChange('workingDaysPerMonth')}
                className={styles.numberInput}
              />
            </label>

            <label className={styles.inputLabel}>
              <span>MCP servers</span>
              <input
                type="number"
                min={0}
                max={20}
                value={inputs.mcpServers}
                onChange={handleNumberChange('mcpServers')}
                className={styles.numberInput}
              />
            </label>

            <label className={styles.inputLabel}>
              <span>File reads per turn</span>
              <input
                type="number"
                min={0}
                max={20}
                value={inputs.fileReadsPerTurn}
                onChange={handleNumberChange('fileReadsPerTurn')}
                className={styles.numberInput}
              />
            </label>
          </div>

          {inputs.model === 'opus' && (
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={inputs.fastMode}
                onChange={(e) => updateField('fastMode', e.target.checked)}
                className={styles.checkbox}
              />
              <span>Fast Mode (6x cost -- Opus only)</span>
            </label>
          )}
        </div>

        <div className={styles.outputPanel}>
          <h2 className={styles.panelTitle}>Monthly Estimate</h2>

          <div className={styles.costSummary}>
            <div className={styles.costCard}>
              <span className={styles.costLabel}>Current</span>
              <span className={styles.costValue}>{formatDollars(result.monthlyCost)}</span>
            </div>
            <div className={`${styles.costCard} ${styles.optimizedCard}`}>
              <span className={styles.costLabel}>Optimized</span>
              <span className={styles.costValue}>{formatDollars(result.optimizedCost)}</span>
            </div>
            <div className={styles.savingsCard}>
              <span className={styles.savingsAmount}>
                Save {formatDollars(result.savings)}/mo
              </span>
              <span className={styles.savingsPercent}>
                {Math.round(result.savingsPercent)}% reduction
              </span>
            </div>
          </div>

          <h3 className={styles.subTitle}>Cost Breakdown</h3>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Category</th>
                <th>Current</th>
                <th>Optimized</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>CLAUDE.md</td>
                <td className={styles.mono}>{formatDollars(result.breakdown.claudeMd)}</td>
                <td className={styles.mono}>{formatDollars(result.optimizedBreakdown.claudeMd)}</td>
              </tr>
              <tr>
                <td>MCP servers</td>
                <td className={styles.mono}>{formatDollars(result.breakdown.mcp)}</td>
                <td className={styles.mono}>{formatDollars(result.optimizedBreakdown.mcp)}</td>
              </tr>
              <tr>
                <td>File reads</td>
                <td className={styles.mono}>{formatDollars(result.breakdown.fileReads)}</td>
                <td className={styles.mono}>{formatDollars(result.optimizedBreakdown.fileReads)}</td>
              </tr>
              <tr>
                <td>History</td>
                <td className={styles.mono}>{formatDollars(result.breakdown.history)}</td>
                <td className={styles.mono}>{formatDollars(result.optimizedBreakdown.history)}</td>
              </tr>
              <tr>
                <td>Output</td>
                <td className={styles.mono}>{formatDollars(result.breakdown.output)}</td>
                <td className={styles.mono}>{formatDollars(result.optimizedBreakdown.output)}</td>
              </tr>
              <tr className={styles.totalRow}>
                <td>Total</td>
                <td className={styles.mono}>{formatDollars(result.monthlyCost)}</td>
                <td className={styles.mono}>{formatDollars(result.optimizedCost)}</td>
              </tr>
            </tbody>
          </table>

          {result.recommendations.length > 0 && (
            <>
              <h3 className={styles.subTitle}>Top Recommendations</h3>
              <ul className={styles.recommendations}>
                {result.recommendations.map((rec, i) => (
                  <li key={i} className={styles.recommendation}>
                    {rec}
                  </li>
                ))}
              </ul>
            </>
          )}

          <button onClick={handleCopy} className={styles.copyButton}>
            {copied ? 'Copied!' : 'Copy as Markdown'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default Calculator
