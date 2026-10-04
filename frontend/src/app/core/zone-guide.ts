import { Component } from '@angular/core';

@Component({standalone:true,selector:'cs-zone-guide',template:`
<details class="zone-guide"><summary>Cómo leer las zonas</summary>
<svg viewBox="85 -6 42 92" role="img" aria-label="Esquema del área: punto de cobro en la esquina superior, zona cercana hacia ese lado, central en el centro y lejana hacia el lado opuesto; exterior fuera del área.">
<rect x="85" y="0" width="35" height="80" fill="#314b40"/>
<rect x="102" y="18" width="18" height="18" fill="#60976e"/>
<rect x="102" y="36" width="18" height="8" fill="#d39740"/>
<rect x="102" y="44" width="18" height="18" fill="#588aa3"/>
<g stroke="white" stroke-width=".3" fill="none"><rect x="102" y="18" width="18" height="44"/><path d="M102 36H120 M102 44H120"/></g>
<g fill="white" font-size="2.8" text-anchor="middle"><text x="111" y="28">Cercana</text><text x="111" y="41">Central</text><text x="111" y="54">Lejana</text><text x="94" y="40">Exterior</text></g>
<circle cx="120" cy="0" r="1" fill="#f7c76b"/>
<text x="119" y="-2" fill="currentColor" font-size="2.6" text-anchor="end">Punto de cobro</text>
<path d="M120 35H124V45H120" fill="none" stroke="white" stroke-width=".5"/>
</svg><p><strong>Cercana:</strong> hacia el lado del cobro. <strong>Central:</strong> hacia el centro del área. <strong>Lejana:</strong> hacia el lado opuesto. <strong>Exterior:</strong> fuera del área.</p>
<p>Las zonas describen el destino del pase, no dónde ocurrió el tiro.</p>
</details>`})
export class ZoneGuide {}
