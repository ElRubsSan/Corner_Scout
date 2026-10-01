import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { clubBadgeSources } from '../core/club-badge-sources.generated';
import { playerPhotoSources } from '../core/player-photo-sources.generated';
import { manualPhotoSources } from '../core/manual-photo-sources.generated';
import { userTakerPhotos } from '../core/user-taker-photos.generated';

@Component({standalone:true,imports:[RouterLink],template:`
<section class="card"><h1>Créditos de imágenes</h1><p>Los retratos identifican a los cobradores de córner de esta muestra histórica; pueden haberse tomado en un año distinto de LaLiga 2015/16. Los archivos con fuente individual registrada conservan sus créditos a continuación.</p>
<ul><li><strong>Beñat Etxebarria.</strong> Fotografía de Memorino, 2012. <a href="https://commons.wikimedia.org/wiki/File:Benat_Etxebarria.jpg" target="_blank" rel="noopener">Archivo original</a> · <a href="https://creativecommons.org/licenses/by-sa/3.0/" target="_blank" rel="noopener">CC BY-SA 3.0</a>. Recorte cuadrado y conversión a WebP.</li>
<li><strong>Roberto Trashorras.</strong> Fotografía de Adrián Estévez (Estevoaei), 2009. <a href="https://commons.wikimedia.org/wiki/File:Roberto_Trashorras.jpg" target="_blank" rel="noopener">Archivo original</a> · <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener">CC BY-SA 4.0</a>. Recorte cuadrado y conversión a WebP.</li></ul>
<h2>Retratos históricos revisados</h2><ul>@for(photo of manual;track photo.id){<li><strong>{{photo.name}}</strong> · {{photo.year}} · {{photo.artist}} · <a [href]="photo.source" target="_blank" rel="noopener">Original</a> · <a [href]="photo.licenseUrl" target="_blank" rel="noopener">{{photo.license}}</a>. Recorte y conversión a WebP.</li>}</ul>
<details><summary>Créditos de otras {{photos.length}} fotografías con procedencia registrada</summary><ol>@for(photo of photos;track photo.id){<li><strong>{{photo.name}}</strong>@if(photo.year){ · fotografía de {{photo.year}}} · {{photo.artist||'Autor indicado en el archivo original'}} · <a [href]="photo.source" target="_blank" rel="noopener">Original</a> · <a [href]="photo.licenseUrl" target="_blank" rel="noopener">{{photo.license}}</a>. Recorte y conversión a WebP.</li>}</ol></details>
<details><summary>Otros {{userPhotos.length}} retratos de cobradores aportados al proyecto</summary><ul>@for(photo of userPhotos;track photo.id){<li>{{photo.name}} · Identidad cotejada con el cobrador de StatsBomb; recorte y conversión a WebP.</li>}</ul></details>
<h2>Escudos de los clubes</h2><p>Los escudos identifican a los clubes de esta muestra histórica. Archivos obtenidos de TheSportsDB.</p><ul>@for(club of clubs;track club.name){<li>{{club.name}} · <a [href]="club.url" target="_blank" rel="noopener">Imagen de origen</a></li>}</ul>
<p>Las fotografías identificativas no representan necesariamente la apariencia del jugador en 2015/16.</p><a routerLink="/">Volver al inicio</a></section>`})
export class Credits {
  readonly clubs=clubBadgeSources;
  readonly photos=playerPhotoSources;
  readonly manual=manualPhotoSources;
  readonly userPhotos=Object.entries(userTakerPhotos).map(([id,name])=>({id:Number(id),name}));
}
