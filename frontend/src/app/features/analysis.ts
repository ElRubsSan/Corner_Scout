import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DecimalPipe, PercentPipe, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Api, Models } from '../core/api';
@Component({standalone:true,imports:[RouterLink,DecimalPipe,PercentPipe,JsonPipe,FormsModule],templateUrl:'./analysis.html'})
export class Analysis {
 api=inject(Api);route=inject(ActivatedRoute);id='';view=signal('summary');run=signal<Models['Run']|null>(null);summary=signal<Models['Summary']|null>(null);corners=signal<Models['Corner'][]>([]);patterns=signal<Models['Pattern'][]>([]);quality=signal<Models['Quality']|null>(null);model=signal<Models['ModelResult']|null>(null);report=signal<Models['Report']|null>(null);plan=signal<string[]>([]);busy=signal(true);reportBusy=signal(false);error=signal('');player='';side='';delivery='';cluster='';
 tabs=[['summary','Dashboard'],['map','Mapa de córners'],['patterns','Patrones'],['report','Reporte táctico'],['quality','Calidad']];
 constructor(){this.route.paramMap.subscribe(params=>{this.view.set(params.get('view')??'summary');const id=params.get('id')??'';if(id!==this.id){this.id=id;void this.load();}});}
 async load(){this.busy.set(true);this.error.set('');try{const [run,s,c,p,q,m,plan]=await Promise.all([this.api.run(this.id),this.api.summary(this.id),this.api.corners(this.id),this.api.patterns(this.id),this.api.quality(this.id),this.api.model(this.id),this.api.plan(this.id)]);this.run.set(run);this.summary.set(s);this.corners.set(c);this.patterns.set(p);this.quality.set(q);this.model.set(m);this.plan.set(plan);}catch(e){this.error.set(String(e));}finally{this.busy.set(false);}}
 filtered(){return this.corners().filter(c=>c.spatial_valid&&(!this.player||c.player===this.player)&&(!this.side||c.side===this.side)&&(!this.delivery||c.delivery===this.delivery)&&(!this.cluster||String(c.cluster)===this.cluster));}
 async generate(){this.reportBusy.set(true);this.error.set('');try{this.report.set(await this.api.report(this.id));}catch(e){this.error.set(String(e));}finally{this.reportBusy.set(false);}}
 download(){const report=this.report();if(!report)return;const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='cornerscout-reporte.json';link.click();URL.revokeObjectURL(url);}
}
