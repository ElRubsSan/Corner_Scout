import { Component, input } from '@angular/core';
import type { Models } from './api';
import { deliveryLabel } from './football-labels';

let nextPitchId = 0;

@Component({
  selector:'cs-pitch',standalone:true,
  template:`<svg class="pitch" [class.mini-pitch]="compact()" viewBox="-3 -3 126 86" role="img" [attr.aria-label]="label()">
    <rect x="0" y="0" width="120" height="80" class="pitch-bg"/>
    @if(mode()==='heat'){
      <defs>
        <clipPath [attr.id]="clipId"><rect width="120" height="80"/></clipPath>
        <filter [attr.id]="blurId" x="-50%" y="-50%" width="200%" height="200%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="2.2"/></filter>
        <radialGradient [attr.id]="glowId">
          <stop offset="0%" stop-color="white" stop-opacity="1"/>
          <stop offset="45%" stop-color="white" stop-opacity=".72"/>
          <stop offset="100%" stop-color="white" stop-opacity="0"/>
        </radialGradient>
        <mask [attr.id]="maskId" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="80">
          @for(cell of heatmap()?.cells??[];track cell.x+':'+cell.y){
            @if(cell.count>0){<ellipse [attr.cx]="cell.x+(heatmap()?.cell_width??0)/2" [attr.cy]="cell.y+(heatmap()?.cell_height??0)/2" [attr.rx]="(heatmap()?.cell_width??0)*.95" [attr.ry]="(heatmap()?.cell_height??0)*.95" [attr.fill]="'url(#'+glowId+')'"/>}
          }
        </mask>
      </defs>
      <g class="heat-layer" [attr.clip-path]="'url(#'+clipId+')'" aria-hidden="true">
        <g [attr.mask]="'url(#'+maskId+')'" [attr.filter]="'url(#'+blurId+')'">
          @for(cell of heatmap()?.cells??[];track cell.x+':'+cell.y){
            @if(cell.count>0){<ellipse class="heat-cell" [attr.cx]="cell.x+(heatmap()?.cell_width??0)/2" [attr.cy]="cell.y+(heatmap()?.cell_height??0)/2" [attr.rx]="(heatmap()?.cell_width??0)*.82" [attr.ry]="(heatmap()?.cell_height??0)*.82" [attr.fill]="heatColor(cell.count,heatmap()?.max_count??0)" [attr.opacity]="opacity(cell.count,heatmap()?.max_count??0)"/>}
          }
        </g>
      </g>
    }@else{
      @for(corner of corners();track corner.event_id){
        <g class="pitch-mark" [class.zone-highlighted]="highlightZone()!==''&&corner.zone===highlightZone()" [attr.opacity]="highlightZone()&&corner.zone!==highlightZone() ? 0.2 : 1"><title>{{corner.player}} · {{deliveryLabel(corner.delivery)}} · destino del pase</title>
          @if(mode()==='passes'){<line class="pass-line" [attr.x1]="corner.x" [attr.y1]="corner.y" [attr.x2]="corner.end_x" [attr.y2]="corner.end_y"/>}
          <circle [attr.cx]="corner.end_x" [attr.cy]="corner.end_y" [attr.r]="highlightZone()&&corner.zone===highlightZone()?1.4:compact()?1.25:.85" [attr.stroke]="highlightZone()&&corner.zone===highlightZone()?'white':null" [attr.stroke-width]="highlightZone()&&corner.zone===highlightZone() ? 0.35 : null" [attr.fill]="corner.shot_within_15s===null?'#d9e3df':corner.shot_within_15s?'#f7c76b':'#c9ee8b'"/>
        </g>
      }
    }
    <g class="pitch-lines" [class.heat-pitch-lines]="mode()==='heat'" pointer-events="none"><rect x="0" y="0" width="120" height="80"/><path d="M60 0V80"/><circle cx="60" cy="40" r="10"/><rect x="0" y="18" width="18" height="44"/><rect x="102" y="18" width="18" height="44"/><rect x="0" y="30" width="6" height="20"/><rect x="114" y="30" width="6" height="20"/></g>
    @if(mode()==='heat'){
      @for(cell of heatmap()?.cells??[];track cell.x+':'+cell.y){
        @if(cell.count>0){<rect class="heat-hit" [attr.x]="cell.x" [attr.y]="cell.y" [attr.width]="heatmap()?.cell_width" [attr.height]="heatmap()?.cell_height"><title>{{cell.count}} de {{heatmap()?.included}} destinos directos en esta cuadrícula</title></rect>}
      }
    }
  </svg>`
})
export class PitchView {
  private readonly instanceId = nextPitchId++;
  readonly clipId = `heat-clip-${this.instanceId}`;
  readonly blurId = `heat-blur-${this.instanceId}`;
  readonly glowId = `heat-glow-${this.instanceId}`;
  readonly maskId = `heat-mask-${this.instanceId}`;
  readonly deliveryLabel=deliveryLabel;
  corners=input<Models['Corner'][]>([]);
  highlightZone=input('');
  heatmap=input<Models['DestinationHeatmap']|null>(null);
  mode=input<'passes'|'destinations'|'heat'>('destinations');
  compact=input(false);
  label=input('Destinos de pases de córner; no son ubicaciones de remate');
  // Styling only: the server's grid counts remain unchanged.
  opacity(count:number,max:number){return count>0&&max>0 ? .5+.48*count/max : 0;}
  heatColor(count:number,max:number):string {
    const intensity=max>0?Math.min(1,Math.max(0,count/max)):0;
    const stops=[[163,230,53],[250,224,71],[251,146,60],[239,68,68]] as const;
    const scaled=intensity*(stops.length-1);
    const index=Math.min(stops.length-2,Math.floor(scaled));
    const fraction=scaled-index;
    const lower=stops[index]??stops[0];
    const upper=stops[index+1]??stops[3];
    const mix=(from:number,to:number)=>Math.round(from+(to-from)*fraction);
    return `rgb(${mix(lower[0],upper[0])},${mix(lower[1],upper[1])},${mix(lower[2],upper[2])})`;
  }
}
