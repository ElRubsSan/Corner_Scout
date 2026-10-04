import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DecimalPipe, PercentPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Api, Models } from '../core/api';
import { dateLabel } from '../core/date-label';
import { deliveryLabel, patternLabel, sideLabel, zoneLabel } from '../core/football-labels';
import { clubImage, playerImage } from '../core/visual-assets';
import { PitchView } from '../core/pitch-view';
import { AnswerMarkdown } from '../core/answer-markdown';
import { ShotExplanation } from '../core/shot-explanation';
import { ZoneGuide } from '../core/zone-guide';

@Component({standalone:true,imports:[RouterLink,DecimalPipe,PercentPipe,FormsModule,PitchView,AnswerMarkdown,ShotExplanation,ZoneGuide],templateUrl:'./analysis.html'})
export class Analysis {
  api=inject(Api);route=inject(ActivatedRoute);router=inject(Router);
  id='';view=signal('summary');
  run=signal<Models['Run']|null>(null);summary=signal<Models['Summary']|null>(null);
  habits=signal<Models['HabitProfile']|null>(null);
  corners=signal<Models['Corner'][]>([]);patterns=signal<Models['Pattern'][]>([]);
  profiles=signal<Models['MatchProfile'][]>([]);heatmap=signal<Models['DestinationHeatmap']|null>(null);
  readonly heatZones=computed(()=>[...(this.heatmap()?.zones??[])].sort((a,b)=>b.count-a.count));
  readonly profilesOldestFirst=computed(()=>[...this.profiles()].reverse());
  quality=signal<Models['Quality']|null>(null);
  model=signal<Models['ModelResult']|null>(null);
  report=signal<Models['Report']|null>(null);agentResult=signal<Models['AgentResponse']|null>(null);
  busy=signal(true);heatBusy=signal(false);reportBusy=signal(false);agentBusy=signal(false);
  error=signal('');heatError=signal('');reportError=signal('');agentError=signal('');
  player='';side='';delivery='';cluster='';patternSide='';mapLayer:'individual'|'heat'='individual';
  question='';askedQuestion=signal('');expandedReport=signal(false);
  readonly tabs=[['summary','Resumen'],['map','Mapa de córners'],['patterns','Patrones'],
    ['report','Reporte táctico'],['quality','Calidad'],['agent','Asistente de evidencia']];
  readonly suggestedQuestions=[
    '¿Qué zona de destino fue más frecuente?',
    '¿Cuántos córners se jugaron en corto?',
    '¿Cuántos córners generaron un tiro en los siguientes 15 segundos?',
    '¿Qué partidos se analizaron?'
  ];
  readonly sideLabel=sideLabel;readonly zoneLabel=zoneLabel;readonly deliveryLabel=deliveryLabel;
  readonly geometricZones=['franja_cercana','franja_central','franja_lejana','fuera_area'];
  zoneCount(label:string):number{return this.habits()?.zones.find(zone=>zone.label===label)?.count??0;}
  selectedDestinationZone=signal('');
  toggleDestinationZone(zone:string):void{this.selectedDestinationZone.update(current=>current===zone?'':zone);}
  readonly patternLabel=patternLabel;readonly dateLabel=dateLabel;
  private loadRequest=0;private heatRequest=0;

  constructor(){this.route.paramMap.subscribe(params=>{
    const old=params.get('view')??'summary';
    this.view.set(({prepare:'summary',explore:'map',matches:'quality'} as Record<string,string>)[old]??old);
    const id=params.get('id')??'';
    if(id!==this.id){this.id=id;void this.load();}
  });}

  async load(){
    const request=++this.loadRequest;const id=this.id;
    this.busy.set(true);this.error.set('');this.heatmap.set(null);this.heatRequest++;
    this.report.set(null);this.agentResult.set(null);this.run.set(null);this.summary.set(null);this.model.set(null);
    try{
      const [run,summary,corners,patterns,quality,profiles,habits,model]=await Promise.all([
        this.api.run(id),this.api.summary(id),this.api.corners(id),this.api.patterns(id),
        this.api.quality(id),this.api.matchProfiles(id),this.api.habits(id),this.api.model(id)
      ]);
      if(request!==this.loadRequest)return;
      this.run.set(run);this.summary.set(summary);this.corners.set(corners);
      this.patterns.set(patterns);this.quality.set(quality);this.profiles.set(profiles);this.habits.set(habits);this.model.set(model);
      if(this.view()==='map'&&this.mapLayer==='heat')void this.loadHeatmap();
    }catch{if(request===this.loadRequest)this.error.set('No pudimos cargar el análisis histórico. Inténtalo de nuevo.');}
    finally{if(request===this.loadRequest)this.busy.set(false);}
  }

  filtered(){return this.corners().filter(c=>c.spatial_valid&&(!this.player||c.player===this.player)&&
    (!this.side||c.side===this.side)&&(!this.delivery||c.delivery===this.delivery)&&
    (!this.cluster||String(c.cluster)===this.cluster));}
  patternCorners(cluster:number){return this.corners().filter(c=>c.cluster===cluster&&c.spatial_valid&&c.delivery==='envio'&&
    (!this.patternSide||c.side===this.patternSide));}
  visiblePatterns(){return this.patterns().map(pattern=>{
    const members=this.patternCorners(pattern.cluster);
    const counts=new Map<string,number>();
    for(const corner of members)counts.set(corner.player,(counts.get(corner.player)??0)+1);
    const taker=[...counts].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))[0]?.[0]??'Sin cobrador conocido';
    return {...pattern,count:members.length,evaluable:members.filter(c=>c.valid_sequence).length,main_taker:taker};
  }).filter(pattern=>pattern.count>0).sort((a,b)=>b.count-a.count||a.cluster-b.cluster);}
  patternTotal(){return this.destinationCorners().filter(c=>!this.patternSide||c.side===this.patternSide).length;}
  destinationCorners(){return this.corners().filter(c=>c.spatial_valid&&c.delivery==='envio');}
  objectiveWinners(){return this.model()?.evaluations.objective_winners??[];}
  objectiveLabel(objective:string){return ({scr15:'Tiro tras córner',short_direct:'En corto o directo',
    delivery_zone:'Zona de envío',corner_count:'Volumen de córners'} as Record<string,string>)[objective]??'Otros resultados';}
  modelLabel(objective:string,winner:string){
    if(objective==='delivery_zone')return 'Sin predicción';
    if(objective==='scr15')return 'Modelo: Tasa histórica de la liga';
    if(winner!=='candidate')return 'Modelo: Tasa histórica';
    if(objective==='short_direct')return 'Modelo: Regresión logística';
    if(objective==='corner_count')return 'Modelo: Regresión de Poisson';
    return 'Modelo evaluado';
  }
  decisionText(objective:string,winner:string){
    if(objective==='scr15')return 'La tasa histórica de la liga fue más fiable que la regresión logística evaluada.';
    if(objective==='delivery_zone')return 'No se ofrece una predicción del siguiente destino.';
    if(winner==='candidate')return 'Seleccionado en evaluación temporal; no garantiza el próximo partido.';
    return 'La tasa histórica fue más fiable en la evaluación temporal; no garantiza el próximo partido.';
  }
  footballText(text:string){return text.replace(/Patron \d+, zona (franja_cercana|franja_central|franja_lejana|fuera_area)/g,
    (_,zone:string)=>`Envíos hacia ${zoneLabel(zone).toLowerCase()}`)
    .replace(/zona (franja_cercana|franja_central|franja_lejana|fuera_area)/g,(_,zone:string)=>zoneLabel(zone).toLowerCase())
    .replace(/\b(franja_cercana|franja_central|franja_lejana|fuera_area|y_bajo|y_alto)\b/g,
      value=>value.startsWith('y_')?sideLabel(value).toLowerCase():zoneLabel(value).toLowerCase())
    .replace(/\bSCR[- ]?15\b/gi,'tiro tras el córner (hasta 15 segundos)');}
  publicText(text:string){return /\b(?:E|L|M)_[A-Z0-9_]+\b|\bcluster[-_]\d+\b|\b(?:candidate|league_reference|missing_api_key)\b/i.test(text)?
    'Esta observación requiere revisión antes de mostrarse.':this.footballText(text);}
  avatar(name:string){return name.split(/\s+/).filter(Boolean).slice(0,2).map(part=>part.charAt(0).toLocaleUpperCase('es')).join('')||'—';}
  clubImage(name:string,id:number|null|undefined){return clubImage(name,id);}
  playerImage(name:string,id:number|null){return playerImage(name,id);}
  onMapChange(){if(this.mapLayer==='heat')void this.loadHeatmap();}
  setMapLayer(layer:'individual'|'heat'){this.mapLayer=layer;if(layer==='heat')void this.loadHeatmap();}
  async loadHeatmap(){
    if(!this.id)return;
    const request=++this.heatRequest;const id=this.id;
    this.heatBusy.set(true);this.heatError.set('');this.heatmap.set(null);
    try{
      const data=await this.api.destinationHeatmap(id,{
        player:this.player||undefined,side:this.side as 'y_bajo'|'y_alto'||undefined,
        delivery:this.delivery as 'corto'|'envio'||undefined,cluster:this.cluster?Number(this.cluster):undefined
      });
      if(request===this.heatRequest&&id===this.id)this.heatmap.set(data);
    }catch{if(request===this.heatRequest)this.heatError.set('No pudimos mostrar estos destinos.');}
    finally{if(request===this.heatRequest)this.heatBusy.set(false);}
  }
  chooseTaker(name:string){this.player=name;void this.router.navigate(['/analysis',this.id,'map']);this.onMapChange();}

  async generate(){
    const id=this.id;this.reportBusy.set(true);this.reportError.set('');
    try{const report=await this.api.report(id);if(id===this.id)this.report.set(report);}
    catch{if(id===this.id)this.reportError.set('No pudimos preparar el texto. Prueba de nuevo; los datos observados siguen disponibles.');}
    finally{if(id===this.id)this.reportBusy.set(false);}
  }
  async askAgent(){
    const question=this.question.trim();if(!question)return;
    const id=this.id;this.agentBusy.set(true);this.agentError.set('');this.agentResult.set(null);
    try{const result=await this.api.agent(id,question);if(id===this.id){this.agentResult.set(result);this.askedQuestion.set(question);}}
    catch{if(id===this.id)this.agentError.set('No pudimos responder con este análisis. Inténtalo de nuevo.');}
    finally{if(id===this.id)this.agentBusy.set(false);}
  }
}
