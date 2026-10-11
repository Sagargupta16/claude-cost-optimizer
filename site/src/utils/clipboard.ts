/**
 * Copy text and flash a "copied" state for two seconds. A denied or missing
 * clipboard (insecure context, permission refused) leaves the state unset
 * instead of throwing an unhandled rejection.
 */
export function copyWithFeedback(text: string, setCopied: (copied: boolean) => void): void {
  navigator.clipboard.writeText(text).then(
    () => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    },
    () => setCopied(false),
  )
}
