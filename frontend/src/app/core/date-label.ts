const formatter = new Intl.DateTimeFormat('es-ES', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'});

/** Parse the calendar date, not a local timestamp: ISO midnight must not shift days. */
export function dateLabel(value: string): string {
  const day = /^\d{4}-\d{2}-\d{2}/.exec(value)?.[0];
  if (!day) return 'Fecha no disponible';
  const date = new Date(`${day}T12:00:00Z`);
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : formatter.format(date);
}
