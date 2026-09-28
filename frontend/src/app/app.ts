import { Component, signal } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({selector:'app-root',standalone:true,imports:[RouterLink,RouterOutlet],template:`
<header><a routerLink="/" class="brand"><span class="brand-mark" aria-hidden="true">⌜</span> CornerScout</a>
<div class="header-actions"><nav aria-label="Navegación principal"><a routerLink="/">Inicio</a><a routerLink="/analysis/new">Nuevo análisis ↗</a></nav>
<button type="button" class="theme-toggle" (click)="toggleTheme()" [attr.aria-label]="theme()==='dark'?'Activar modo claro':'Activar modo oscuro'" [attr.aria-pressed]="theme()==='dark'">{{theme()==='dark'?'☀ Modo claro':'☾ Modo oscuro'}}</button></div></header>
<div class="historical">ANÁLISIS PREPARTIDO · LaLiga 2015/16 · Datos históricos, no en vivo</div>
<main id="main"><router-outlet /></main><footer>Datos: <a href="https://github.com/statsbomb/open-data" target="_blank" rel="noopener">StatsBomb Open Data</a> · MVP académico · Córners ofensivos · Sin video ni tracking</footer>`})
export class App {
  theme = signal<'light' | 'dark'>('light');

  constructor() {
    try { this.theme.set(localStorage.getItem('cornerscout-theme') === 'dark' ? 'dark' : 'light'); } catch { /* Storage may be unavailable. */ }
    this.applyTheme();
  }

  toggleTheme() {
    this.theme.update(value => value === 'dark' ? 'light' : 'dark');
    this.applyTheme();
    try { localStorage.setItem('cornerscout-theme', this.theme()); } catch { /* Theme still works for this visit. */ }
  }

  private applyTheme() { document.documentElement.dataset['theme'] = this.theme(); }
}
