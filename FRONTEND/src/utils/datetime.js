// Renders a timestamp using the user's preferred timezone (Profile > Settings
// > System Preferences). Falls back to the browser's local timezone if none
// is set yet, so this is always safe to call.
export function formatDateTime(value, timeZone) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  try {
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: timeZone || undefined,
      year: 'numeric', month: 'short', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    }).format(d);
  } catch {
    // Unknown/invalid IANA timezone string — fall back rather than crash the page.
    return d.toLocaleString();
  }
}
