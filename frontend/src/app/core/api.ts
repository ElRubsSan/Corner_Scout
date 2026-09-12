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
  return createClient<paths>({baseUrl:config.apiBaseUrl});
 }
 async teams(){return this.unwrap(await (await this.client).GET('/api/v1/teams'));}
 async matches(rival:string,before?:string,limit=380){return this.unwrap(await (await this.client).GET('/api/v1/matches',{params:{query:{rival,before,limit}}}));}
 async create(body:Models['RunRequest']){return this.unwrap(await (await this.client).POST('/api/v1/scouting-runs',{body}));}
 async run(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}',{params:{path:{run_id:id}}}));}
 async summary(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/summary',{params:{path:{run_id:id}}}));}
 async corners(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/corners',{params:{path:{run_id:id}}}));}
 async patterns(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/patterns',{params:{path:{run_id:id}}}));}
 async quality(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/quality',{params:{path:{run_id:id}}}));}
 async model(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/model',{params:{path:{run_id:id}}}));}
 async plan(id:string){return this.unwrap(await (await this.client).GET('/api/v1/scouting-runs/{run_id}/report-plan',{params:{path:{run_id:id}}}));}
 async report(id:string){return this.unwrap(await (await this.client).POST('/api/v1/scouting-runs/{run_id}/report',{params:{path:{run_id:id}}}));}
 private unwrap<T>(result:{data?:T;error?:unknown;response:Response}):T {
  if(result.data===undefined){const err=result.error as {detail?:unknown}|undefined; throw new Error(typeof err?.detail==='string'?err.detail:`Error ${result.response.status}: revise el backend y los datos procesados`);}
  return result.data;
 }
}
