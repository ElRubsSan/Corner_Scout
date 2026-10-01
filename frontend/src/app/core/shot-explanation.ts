import { Component } from '@angular/core';

@Component({selector:'cs-shot-explanation',standalone:true,template:`
<details class="metric-help shot-help">
  <summary>¿Cómo se cuenta el tiro tras el córner?</summary>
  <div class="shot-help-content">
    <h3>¿Cuándo cuenta un tiro tras el córner?</h3>
    <ol class="shot-steps" aria-label="Cómo se cuenta un córner con tiro">
      <li>
        <span class="shot-step-icon" aria-hidden="true">⚑</span>
        <span>
          <small>Inicio</small>
          <strong>Se cobra el córner</strong>
        </span>
      </li>
      <li>
        <span class="shot-step-icon" aria-hidden="true">◷</span>
        <span>
          <small>Ventana máxima</small>
          <strong>Hasta <b>15 segundos</b></strong>
        </span>
      </li>
      <li>
        <span class="shot-step-icon" aria-hidden="true">◎</span>
        <span>
          <small>Resultado</small>
          <strong>Hay al menos un tiro</strong>
        </span>
      </li>
    </ol>
    <div class="shot-rule-grid">
      <section class="shot-rule">
        <h4>La secuencia termina antes si…</h4>
        <ul class="shot-icon-list">
          <li>
            <span class="shot-rule-icon" aria-hidden="true">⇄</span>
            <span>El equipo pierde la posesión.</span>
          </li>
          <li>
            <span class="shot-rule-icon" aria-hidden="true">◷</span>
            <span>Termina el periodo.</span>
          </li>
          <li>
            <span class="shot-rule-icon" aria-hidden="true">⚑</span>
            <span>Se cobra otro córner.</span>
          </li>
        </ul>
      </section>
      <section class="shot-rule">
        <h4>Dos detalles importantes</h4>
        <ul class="shot-icon-list">
          <li>
            <span class="shot-rule-icon" aria-hidden="true">✓</span>
            <div class="shot-rule-copy">
              <strong>Justo a los 15 segundos también cuenta</strong>
              <span>Siempre que no haya ocurrido otro cierre antes.</span>
            </div>
          </li>
          <li>
            <span class="shot-rule-icon" aria-hidden="true">ⓘ</span>
            <div class="shot-rule-copy">
              <strong>Los córners no evaluables quedan fuera del porcentaje</strong>
              <span>No se cuentan como córners sin tiro.</span>
            </div>
          </li>
        </ul>
      </section>
    </div>
    <p class="shot-technical">
      <span>Nombre técnico: <strong>SCR-15</strong></span>
      <span>Mide si hubo tiro, no si hubo gol.</span>
    </p>
  </div>
</details>`})
export class ShotExplanation {}
