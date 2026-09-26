import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DecimalPipe, PercentPipe, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Api, Models } from '../core/api';
@Component({standalone:true,imports:[RouterLink,DecimalPipe,PercentPipe,JsonPipe,FormsModule],templateUrl:'./analysis.html'})
export class Analysis {
 api=inject(Api);route=inject(ActivatedRoute);id='';view=signal('summary');run=signal<Models['Run']|null>(null);summary=signal<Models['Summary']|null>(null);corners=signal<Models['Corner'][]>([]);patterns=signal<Models['Pattern'][]>([]);quality=signal<Models['Quality']|null>(null);model=signal<Models['ModelResult']|null>(null);report=signal<Models['Report']|null>(null);agentResult=signal<Models['AgentResponse']|null>(null);plan=signal<string[]>([]);busy=signal(true);reportBusy=signal(false);agentBusy=signal(false);error=signal('');player='';side='';delivery='';cluster='';question='';askedQuestion=signal('');
 tabs=[['summary','Dashboard'],['map','Mapa de córners'],['patterns','Patrones'],['report','Reporte táctico'],['agent','Agente'],['quality','Calidad']];
 readonly objectiveOrder=['scr15','short_direct','delivery_zone','corner_count'];
 constructor(){this.route.paramMap.subscribe(params=>{this.view.set(params.get('view')??'summary');const id=params.get('id')??'';if(id!==this.id){this.id=id;void this.load();}});}
 async load(){this.busy.set(true);this.error.set('');try{const [run,s,c,p,q,m,plan]=await Promise.all([this.api.run(this.id),this.api.summary(this.id),this.api.corners(this.id),this.api.patterns(this.id),this.api.quality(this.id),this.api.model(this.id),this.api.plan(this.id)]);this.run.set(run);this.summary.set(s);this.corners.set(c);this.patterns.set(p);this.quality.set(q);this.model.set(m);this.plan.set(plan);}catch(e){this.error.set(String(e));}finally{this.busy.set(false);}}
 filtered(){return this.corners().filter(c=>c.spatial_valid&&(!this.player||c.player===this.player)&&(!this.side||c.side===this.side)&&(!this.delivery||c.delivery===this.delivery)&&(!this.cluster||String(c.cluster)===this.cluster));}
 objectiveWinners(){return [...(this.model()?.evaluations.objective_winners??[])].sort((a,b)=>this.objectiveOrder.indexOf(a.objective)-this.objectiveOrder.indexOf(b.objective));}
 scr15UsesLeagueReference(){return this.objectiveWinners().some(result=>result.objective==='scr15'&&result.winner==='league_reference');}
 objectiveLabel(objective:string){return ({scr15:'SCR-15',short_direct:'Córner corto/directo',delivery_zone:'Zona de envío',corner_count:'Cantidad de córners'} as Record<string,string>)[objective]??objective;}
 winnerLabel(winner:string){return ({candidate:'Modelo candidato seleccionado',league_reference:'Referencia liguera',historical_baseline:'Histórico del equipo',not_modeled:'No modelado',not_modelled:'No modelado',logistic_regression:'Regresión logística',poisson_regression:'Regresión de Poisson'} as Record<string,string>)[winner]??winner.replaceAll('_',' ');}
 justificationLabel(justification:string){return justification.replace('candidate passed','El candidato superó').replace('development windows','ventanas de desarrollo').replace('persistence rho','persistencia rho').replace('support min','soporte mínimo').replace('teams min','equipos mínimos').replace('persistence','persistencia').replace('variance/mean','varianza/media').replace('conditional dispersion','dispersión condicional').replace('family','familia');}
 async generate(){this.reportBusy.set(true);this.error.set('');try{this.report.set(await this.api.report(this.id));}catch(e){this.error.set(String(e));}finally{this.reportBusy.set(false);}}
 async askAgent(){const question=this.question.trim();if(!question)return;this.agentBusy.set(true);this.error.set('');this.agentResult.set(null);try{this.agentResult.set(await this.api.agent(this.id,question));this.askedQuestion.set(question);}catch(e){this.error.set(String(e));}finally{this.agentBusy.set(false);}}
 download(){const report=this.report();if(!report)return;const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='cornerscout-reporte.json';link.click();URL.revokeObjectURL(url);}
}
