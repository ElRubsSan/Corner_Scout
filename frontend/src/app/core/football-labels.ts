// Display-only terminology. API values and evidence identifiers remain unchanged.
export function sideLabel(value: string): string {
  return ({ y_bajo: 'Córner desde la izquierda', y_alto: 'Córner desde la derecha' } as Record<string, string>)[value] ?? 'Lado no disponible';
}

export function zoneLabel(value: string): string {
  return ({
    franja_cercana: 'Zona cercana al punto de cobro',
    franja_central: 'Zona central del área',
    franja_lejana: 'Zona alejada del punto de cobro',
    fuera_area: 'Fuera del área',
    no_disponible: 'Destino no disponible',
  } as Record<string, string>)[value] ?? 'Zona sin clasificar';
}

export function deliveryLabel(value: string): string {
  return ({ corto: 'En corto', envio: 'Envío directo', desconocido: 'Sin clasificar' } as Record<string, string>)[value] ?? 'Sin clasificar';
}

export function patternLabel(zone: string): string {
  return `Envíos hacia ${zoneLabel(zone).toLowerCase()}`;
}
