import { Injectable } from '@angular/core';
import createClient from 'openapi-fetch';
import type { paths, components } from './api.generated';
export type Models = components['schemas'];
@Injectable({providedIn:'root'})
export class Api {
 private client = this.initialize();
 private async initialize() {
  const response = await fetch('/config.json');
  if (!response.ok) throw new Error('No se pudo leer la configuración del backend');
  const config: {apiBaseUrl:string} = await response.json();
  const client=createClient<paths>({baseUrl:config.apiBaseUrl});
  client.use({
   onRequest({request}){
    const id=/\/scouting-runs\/([a-f0-9]{64})(?:\/|$)/.exec(new URL(request.url).pathname)?.[1];
    if(id){const token=sessionStorage.getItem(`cornerscout-run-${id}`);if(token)request.headers.set('X-CornerScout-Run',token);}
    return request;
   },
   async onResponse({request,response}){
    const token=response.headers.get('X-CornerScout-Run');
    if(token&&request.method==='POST'&&new URL(request.url).pathname.endsWith('/scouting-runs')&&response.ok){
     const run=await response.clone().json() as {run_id:string};
     sessionStorage.setItem(`cornerscout-run-${run.run_id}`,token);
    }
    return response;
   }
  });
  return client;
 }
 async teams(){return this.unwrap(await (await this.client).GET('/api/v1/teams'));}
 async matches(rival:string,before?:string,limit=380){return this.unwrap(await (await this.client).GET('/api/v1/matches',{params:{query:{rival,before,limit}}}));}
 async create(body:Models['RunRequest']){return this.unwrap(await (await this.client).POST('/api/v1/scouting-runs',{body}));}
 async run(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}',{params:{path:{run_id:id}}}));}
 async summary(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/summary',{params:{path:{run_id:id}}}));}
 async habits(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/habits',{params:{path:{run_id:id}}}));}
 async corners(id:string){
  const all:Models['Corner'][]=[];
  const limit=500;
  for(let offset=0;;offset+=limit){
   const page=this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/corners',{params:{path:{run_id:id},query:{offset,limit}}}));
   all.push(...page);
   if(page.length<limit)return all;
  }
 }
 async matchProfiles(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/matches-profile',{params:{path:{run_id:id}}}));}
 async destinationHeatmap(id:string,filters:{player?:string;side?:'y_bajo'|'y_alto';delivery?:'corto'|'envio'|'desconocido';cluster?:number}){
  return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/destination-heatmap',{params:{path:{run_id:id},query:filters}}));
 }
 async patterns(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/patterns',{params:{path:{run_id:id}}}));}
 async quality(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/quality',{params:{path:{run_id:id}}}));}
 async model(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/model',{params:{path:{run_id:id}}}));}
 async plan(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/report-plan',{params:{path:{run_id:id}}}));}
 async report(id:string){return this.unwrap(await (await this.client).POST('/api/v1/scouting-runs/{run_id}/report',{params:{path:{run_id:id}}}));}
 async agent(id:string,question:string){return this.unwrap(await (await this.client).POST('/api/v1/scouting-runs/{run_id}/agent',{params:{path:{run_id:id}},body:{question}}));}
 private unwrap<T>(result:{data?:T;error?:unknown;response:Response}):T {
   if(result.data===undefined){
    const messages:Record<number,string>={
     404:'No encontramos este análisis o equipo. Crea uno nuevo.',
     409:'La información de este análisis cambió. Crea un análisis nuevo.',
     422:'No se puede completar la selección. Comprueba el partido y los ocho encuentros anteriores.',
     503:'Los datos históricos no están disponibles ahora. Inténtalo más tarde.'
    };
    throw new Error(messages[result.response.status]??'No se pudo completar la consulta. Inténtalo de nuevo.');
   }
  return result.data;
 }
}
