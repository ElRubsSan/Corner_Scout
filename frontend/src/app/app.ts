import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';
@Component({selector:'app-root',standalone:true,imports:[RouterLink,RouterOutlet],template:`
<header><a routerLink="/" class="brand"><span class="brand-mark">⌜</span> CornerScout</a><nav><a routerLink="/">Inicio</a><a routerLink="/analysis/new">Nuevo análisis ↗</a></nav></header>
<div class="historical">LABORATORIO DE SCOUTING · LaLiga 2015/16 · Datos históricos, no en vivo</div>
<main><router-outlet /></main><footer>Datos: <a href="https://github.com/statsbomb/open-data" target="_blank" rel="noopener">StatsBomb Open Data</a> · MVP académico · Córners ofensivos · Sin video ni tracking</footer>`})
export class App {}
