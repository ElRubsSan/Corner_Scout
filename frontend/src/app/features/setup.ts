import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Api, Models } from '../core/api';
import { dateLabel } from '../core/date-label';
import { clubImage } from '../core/visual-assets';

@Component({standalone:true,imports:[FormsModule],template:`
<div class="eyebrow">NUEVO ANÁLISIS · DATOS HISTÓRICOS</div><h1>Prepara la defensa del córner.</h1>
<p class="section-intro">Elige el rival y el partido que preparas. Estudiaremos sus ocho encuentros anteriores: el partido elegido nunca entra en la muestra.</p>
@if(error()){<div role="alert" class="alert">{{error()}} <button type="button" class="secondary" (click)="reload()">Reintentar</button></div>}
<div class="grid md:grid-cols-2 gap-6"><section class="card"><span class="eyebrow">PASO 1 / SELECCIONAR</span><h2>Rival y corte</h2>
@if(loadingTeams()){<p role="status">Cargando equipos…</p>}
<label>Equipo rival<select [(ngModel)]="rival" (ngModelChange)="changed()" [disabled]="loadingTeams()||busy()"><option value="" disabled>Selecciona un rival</option>@for(t of teams();track t.name){<option [value]="t.name">{{t.name}}</option>}</select></label>
<label>Cómo elegir la muestra<select [(ngModel)]="mode" (ngModelChange)="resetWindow()" [disabled]="busy()"><option value="match">Partido que preparas</option><option value="date">Hasta una fecha histórica</option></select></label>
 @if(mode==='date'){<label>Fecha de corte (exclusiva)<input type="date" [(ngModel)]="cutoff" (ngModelChange)="resetWindow()" min="2015-08-01" max="2016-06-01" [disabled]="busy()"></label>}
 @else{<label>Partido objetivo<select [(ngModel)]="target" (ngModelChange)="resetWindow()" [disabled]="busy()"><option [ngValue]="null">Selecciona un partido</option>@for(m of targets();track m.match_id){<option [ngValue]="m.match_id">{{dateLabel(m.match_date)}} · {{m.home_team}} — {{m.away_team}}</option>}</select></label>}
<label>Destinatario del informe (opcional)<select [(ngModel)]="analyst" [disabled]="busy()"><option value="">Sin especificar</option>@for(t of teams();track t.name){<option [value]="t.name">{{t.name}}</option>}</select></label>
<button type="button" (click)="preview()" [disabled]="busy()||loadingTeams()||!rival">Ver ocho partidos anteriores</button></section>
<section class="card"><span class="eyebrow">PASO 2 / CONFIRMAR</span><h2>Ventana histórica</h2>
@if(busy()&&!creating()){<p role="status">Consultando partidos anteriores…</p>}
@if(!window().length&&!busy()&&!previewed()){<p>Selecciona rival y corte para consultar la ventana. No se incluyen partidos del día de corte.</p>}
@if(previewed()&&!window().length&&!busy()){<p class="alert">Datos insuficientes: 0 de 8 partidos anteriores al corte.</p>}
  <ol class="matches">@for(m of windowOldestFirst();track m.match_id){<li><small>{{dateLabel(m.match_date)}}</small><div class="scoreboard"><span class="score-team">@if(clubBadge(m.home_team,m.home_team_id);as badge){<img [src]="badge" alt="" loading="lazy" (error)="$any($event.target).remove()">}<span>{{m.home_team}}</span></span><strong class="score">{{m.home_score===null||m.home_score===undefined?'—':m.home_score}} : {{m.away_score===null||m.away_score===undefined?'—':m.away_score}}</strong><span class="score-team">@if(clubBadge(m.away_team,m.away_team_id);as badge){<img [src]="badge" alt="" loading="lazy" (error)="$any($event.target).remove()">}<span>{{m.away_team}}</span></span></div></li>}</ol>
@if(window().length===8){<p class="notice">Ventana completa · 8 de 8 partidos. Fuente: StatsBomb Open Data, LaLiga 2015/16.</p><button type="button" (click)="execute()" [disabled]="busy()">{{creating()?'Creando análisis…':'Crear análisis →'}}</button>}
@else if(window().length){<p class="alert">Datos insuficientes: {{window().length}} de 8 partidos.</p>}
<small>Este análisis utiliza datos históricos; no describe la forma actual del rival.</small></section></div>`})
export class Setup {
  readonly dateLabel=dateLabel;
  api=inject(Api);router=inject(Router);teams=signal<Models['Team'][]>([]);targets=signal<Models['Match'][]>([]);window=signal<Models['Match'][]>([]);
  readonly windowOldestFirst=computed(()=>[...this.window()].sort((a,b)=>a.match_date.localeCompare(b.match_date)||a.kick_off.localeCompare(b.kick_off)||a.match_id-b.match_id));
  loadingTeams=signal(true);busy=signal(false);creating=signal(false);previewed=signal(false);error=signal('');
  rival='Barcelona';analyst='';cutoff='2016-03-01';mode='match';target:number|null=null;
  private targetRequest=0;

  constructor(){void this.reload();}
  async reload(){this.loadingTeams.set(true);this.error.set('');try{this.teams.set(await this.api.teams());await this.changed();}catch{this.error.set('No pudimos cargar los equipos. Reintenta.');}finally{this.loadingTeams.set(false);}}
  resetWindow(){this.window.set([]);this.previewed.set(false);this.error.set('');}
  async changed(){this.resetWindow();this.target=null;const request=++this.targetRequest;this.targets.set([]);if(!this.rival)return;try{const matches=await this.api.matches(this.rival);if(request===this.targetRequest)this.targets.set(matches);}catch{if(request===this.targetRequest)this.error.set('No pudimos consultar los partidos de este rival.');}}
  async preview(){this.error.set('');this.busy.set(true);this.previewed.set(false);this.window.set([]);try{const cutoff=this.mode==='match'?this.targets().find(m=>m.match_id===this.target)?.match_date:this.cutoff;if(!cutoff){this.error.set('Selecciona primero un partido o fecha.');return;}this.window.set(await this.api.matches(this.rival,cutoff,8));this.previewed.set(true);}catch{this.error.set('No pudimos consultar estos partidos. Reintenta.');}finally{this.busy.set(false);}}
  async execute(){if(this.window().length!==8||this.busy())return;this.busy.set(true);this.creating.set(true);this.error.set('');try{const run=await this.api.create({rival:this.rival,analyst:this.analyst||null,cutoff_date:this.mode==='date'?this.cutoff:null,target_match_id:this.mode==='match'?this.target:null,expected_match_ids:this.window().map(m=>m.match_id)});await this.router.navigate(['/analysis',run.run_id,'summary']);}catch{this.error.set('No pudimos crear este análisis. Confirma los ocho partidos y reintenta.');}finally{this.busy.set(false);this.creating.set(false);}}
  clubBadge(name:string,id:number|null|undefined){return clubImage(name,id);}
}
