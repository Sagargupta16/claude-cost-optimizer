import { useState, useMemo, useCallback } from 'react'
import { scoreBadge, type BadgeInputs } from '../utils/badge'
import styles from './BadgeChecker.module.css'

const defaultInputs: BadgeInputs = {
  claudeMdLines: 100,
  claudeIgnoreEntries: 0,
  hasModelConfigured: false,
  hasBudgetCap: false,
  mcpServers: 2,
}

function BadgeChecker() {
  const [inputs, setInputs] = useState<BadgeInputs>(defaultInputs)
  const [copied, setCopied] = useState(false)

  const result = useMemo(() => scoreBadge(inputs), [inputs])

  const updateField = useCallback(
    <K extends keyof BadgeInputs>(field: K, value: BadgeInputs[K]) => {
      setInputs((prev) => ({ ...prev, [field]: value }))
    },
    [],
  )

  const handleNumberChange = useCallback(
    (field: keyof BadgeInputs) => (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = parseInt(e.target.value, 10)
      if (!isNaN(val) && val >= 0) {
        updateField(field, val as BadgeInputs[typeof field])
      }
    },
    [updateField],
  )

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(result.badgeMarkdown).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [result.badgeMarkdown])

  const activeRecommendations = result.categories.filter((c) => c.recommendation)

  return (
    <div className={styles.checker}>
      <h1 className={styles.title}>Badge Checker</h1>
      <p className={styles.subtitle}>
        Score your Claude Code setup and earn a grade badge for your repo.
      </p>

      <div className={styles.grid}>
        <div className={styles.inputPanel}>
          <h2 className={styles.panelTitle}>Your Setup</h2>

          <label className={styles.inputLabel}>
            <span>CLAUDE.md line count</span>
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
            <span>.claudeignore entry count</span>
            <input
              type="number"
              min={0}
              max={100}
              value={inputs.claudeIgnoreEntries}
              onChange={handleNumberChange('claudeIgnoreEntries')}
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

          <div className={styles.checkboxGroup}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={inputs.hasModelConfigured}
                onChange={(e) => updateField('hasModelConfigured', e.target.checked)}
                className={styles.checkbox}
              />
              <span>Default model configured</span>
            </label>

            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={inputs.hasBudgetCap}
                onChange={(e) => updateField('hasBudgetCap', e.target.checked)}
                className={styles.checkbox}
              />
              <span>Budget cap set</span>
            </label>
          </div>
        </div>

        <div className={styles.outputPanel}>
          <div className={styles.gradeDisplay}>
            <span
              className={styles.grade}
              style={{ color: result.gradeColor }}
            >
              {result.grade}
            </span>
            <span className={styles.scoreText}>
              {result.totalScore} / 100
            </span>
          </div>

          <h3 className={styles.subTitle}>Score Breakdown</h3>
          <div className={styles.categories}>
            {result.categories.map((cat) => (
              <div key={cat.name} className={styles.category}>
                <div className={styles.categoryHeader}>
                  <span className={styles.categoryName}>{cat.name}</span>
                  <span className={styles.categoryScore}>
                    {cat.score} / {cat.maxScore}
                  </span>
                </div>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{
                      width: `${(cat.score / cat.maxScore) * 100}%`,
                      backgroundColor:
                        cat.score === cat.maxScore
                          ? 'var(--accent-green)'
                          : cat.score >= cat.maxScore * 0.6
                            ? 'var(--warning-yellow)'
                            : 'var(--error-red)',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <h3 className={styles.subTitle}>Badge Preview</h3>
          <div className={styles.badgePreview}>
            <img
              src={result.badgeUrl}
              alt={`Grade: ${result.grade}`}
              className={styles.badgeImg}
            />
          </div>

          <button onClick={handleCopy} className={styles.copyButton}>
            {copied ? 'Copied!' : 'Copy Badge Markdown'}
          </button>

          {activeRecommendations.length > 0 && (
            <>
              <h3 className={styles.subTitle}>Recommendations</h3>
              <ul className={styles.recommendations}>
                {activeRecommendations.map((cat) => (
                  <li key={cat.name} className={styles.recommendation}>
                    <strong>{cat.name}:</strong> {cat.recommendation}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default BadgeChecker
