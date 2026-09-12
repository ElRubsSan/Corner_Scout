import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Api, Models } from '../core/api';
@Component({standalone:true,imports:[FormsModule],template:`
<div class="eyebrow">NUEVO ANÁLISIS</div><h1>Conoce al rival.</h1><p>Confirma los ocho encuentros que formarán la evidencia del reporte.</p>
@if(error()){<div role="alert" class="alert">{{error()}}</div>}
<div class="grid md:grid-cols-2 gap-6"><section class="card"><h2>Configuración</h2>
<label>Equipo rival<select [(ngModel)]="rival" (ngModelChange)="changed()">@for(t of teams();track t.name){<option [value]="t.name">{{t.name}}</option>}</select></label>
<label>Tipo de corte<select [(ngModel)]="mode" (ngModelChange)="window.set([])"><option value="date">Fecha de corte</option><option value="match">Partido objetivo</option></select></label>
@if(mode==='date'){<label>Fecha de corte (exclusiva)<input type="date" [(ngModel)]="cutoff" (ngModelChange)="window.set([])" min="2015-08-01" max="2016-06-01"></label>}
@else{<label>Partido objetivo<select [(ngModel)]="target" (ngModelChange)="window.set([])"><option [ngValue]="null">Selecciona un partido</option>@for(m of targets();track m.match_id){<option [ngValue]="m.match_id">{{m.match_date}} · {{m.home_team}} — {{m.away_team}}</option>}</select></label>}
<label>Equipo analista (contexto visual)<select [(ngModel)]="analyst"><option value="">Sin especificar</option>@for(t of teams();track t.name){<option [value]="t.name">{{t.name}}</option>}</select></label>
<button (click)="preview()" [disabled]="busy()||!rival">Ver ocho partidos anteriores</button></section>
<section class="card"><h2>Ventana histórica</h2>@if(busy()){<p role="status">Consultando partidos…</p>}
@if(!window().length&&!busy()&&!previewed()){<p>Selecciona rival y corte para ver los encuentros. No se incluyen partidos del día de corte.</p>}
@if(previewed()&&!window().length&&!busy()){<p class="alert">Datos insuficientes: 0 de 8 partidos anteriores al corte.</p>}
<ol class="matches">@for(m of window();track m.match_id){<li><small>{{m.match_date}} · #{{m.match_id}}</small><strong>{{m.home_team}} — {{m.away_team}}</strong></li>}</ol>
@if(window().length===8){<button (click)="execute()" [disabled]="busy()">Confirmar y analizar →</button>}@else if(window().length){<p class="alert">Datos insuficientes: {{window().length}} de 8 partidos.</p>}</section></div>`})
export class Setup {
 api=inject(Api);router=inject(Router);teams=signal<Models['Team'][]>([]);targets=signal<Models['Match'][]>([]);window=signal<Models['Match'][]>([]);busy=signal(false);previewed=signal(false);error=signal('');rival='Barcelona';analyst='';cutoff='2016-03-01';mode='date';target:number|null=null;
 constructor(){this.api.teams().then(t=>{this.teams.set(t);return this.changed();}).catch(e=>this.error.set(String(e.message??e)));}
 async changed(){this.window.set([]);this.target=null;try{this.targets.set(await this.api.matches(this.rival));}catch(e){this.error.set(String(e));}}
 async preview(){this.error.set('');this.busy.set(true);this.previewed.set(false);this.window.set([]);try{const cutoff=this.mode==='match'?this.targets().find(m=>m.match_id===this.target)?.match_date:this.cutoff;if(!cutoff)throw new Error('Selecciona una fecha o partido');this.window.set(await this.api.matches(this.rival,cutoff,8));this.previewed.set(true);}catch(e){this.error.set(String(e));}finally{this.busy.set(false);}}
 async execute(){this.busy.set(true);this.error.set('');try{const run=await this.api.create({rival:this.rival,analyst:this.analyst||null,cutoff_date:this.mode==='date'?this.cutoff:null,target_match_id:this.mode==='match'?this.target:null,expected_match_ids:this.window().map(m=>m.match_id)});await this.router.navigate(['/analysis',run.run_id,'summary']);}catch(e){this.error.set(String(e));}finally{this.busy.set(false);}}
}
