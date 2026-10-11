import styles from './homeCharts.module.css'

interface RideBarProps {
  x: number
  y: number
  /** Final bar width in px; the bar scales up to it from 0. */
  width: number
  height: number
  color: string
  label: string
  labelClass?: string
  shown: boolean
  delay: number
}

/** One horizontal bar that grows from 0 when `shown`, with its value label riding the tip. */
function RideBar({ x, y, width, height, color, label, labelClass, shown, delay }: Readonly<RideBarProps>) {
  const w = Math.max(width, 2)
  const timing = { transitionDelay: `${delay}ms` }
  return (
    <>
      <rect
        x={x}
        y={y}
        width={w}
        height={height}
        rx={2}
        fill={color}
        className={styles.growBar}
        style={{ ...timing, transform: `scaleX(${shown ? 1 : 0})` }}
      />
      <text
        x={x + 6}
        y={y + height - 1}
        className={`${styles.ride} ${labelClass ?? styles.value}`}
        style={{ ...timing, transform: `translateX(${shown ? w : 0}px)`, opacity: shown ? 1 : 0 }}
      >
        {label}
      </text>
    </>
  )
}

export default RideBar
