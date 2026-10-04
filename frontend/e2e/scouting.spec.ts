import { test, expect } from '@playwright/test';
import { clubNames } from '../src/app/core/visual-entities.generated';
import { dateLabel } from '../src/app/core/date-label';
import { userTakerPhotos } from '../src/app/core/user-taker-photos.generated';

const technical=/\b(?:E|L|M)_[A-Z0-9_]+\b|\bcluster[-_]\d+\b|\b(?:missing_api_key|source_manifest_sha256|run_id|event_id|dataset_version|canonical_runs|tool_calls|tokens)\b|[a-f0-9]{64}/i;

async function coachText(page: import('@playwright/test').Page){
  const text=await page.locator('body').textContent();
  expect(text).not.toMatch(technical);
  const labels=await page.locator('[aria-label],[title]').evaluateAll(elements=>elements.flatMap(element=>[
    element.getAttribute('aria-label')??'',element.getAttribute('title')??''
  ]).join(' '));
  expect(labels).not.toMatch(technical);
}

/** The rendered list must read oldest to newest, the opposite of the canonical window order. */
async function expectOldestFirst(page: import('@playwright/test').Page, selector:string, expected:string[]){
  const rendered=await page.locator(selector).evaluateAll(nodes=>nodes.map(node=>
    (node.querySelector('time')??node.querySelector('small'))?.textContent?.trim()??''
  ));
  expect(rendered).toEqual(expected);
}

test('six tactical tabs tell a visual, grounded story',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');await coachText(page);
  await expect(page.locator('.historical')).toContainText('LaLiga 2015/16 · Datos históricos, no en vivo');
  await page.getByRole('link',{name:'Preparar un análisis'}).click();
  await page.getByLabel('Cómo elegir la muestra').selectOption('date');
  await page.getByLabel('Fecha de corte (exclusiva)').fill('2016-03-01');
  await page.getByRole('button',{name:'Ver ocho partidos anteriores'}).click();
  await expect(page.locator('ol.matches li')).toHaveCount(8);
  const window=await (await page.request.get('http://127.0.0.1:8001/api/v1/matches?rival=Barcelona&before=2016-03-01&limit=8')).json() as {match_date:string;home_score:number|null;away_score:number|null;home_team_id:number|null;away_team_id:number|null}[];
  const oldestFirst=[...window].reverse().map(match=>dateLabel(match.match_date));
  await expectOldestFirst(page,'ol.matches li',oldestFirst);
  for(const match of window.slice(0,2)){
    expect(match.home_score!==null&&match.away_score!==null).toBe(true);
    expect(match.home_team_id!==null&&match.away_team_id!==null).toBe(true);
  }
  await expect(page.locator('ol.matches .score').first()).toContainText(`${window[window.length-1].home_score} : ${window[window.length-1].away_score}`);
  const stepTwoBadges=page.locator('ol.matches li').first().locator('img[src^="/media/clubs/"]');
  await expect(stepTwoBadges).toHaveCount(2);
  await expect(stepTwoBadges.first()).toBeVisible();
  await expect.poll(()=>stepTwoBadges.first().evaluate(image=>(image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await page.screenshot({path:'test-results/selection-visual-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Crear análisis'}).click();
  await expect(page.getByRole('navigation',{name:'Secciones del análisis'}).getByRole('link')).toHaveCount(6);
  await expect(page.getByRole('heading',{name:'¿Qué debemos preparar?'})).toBeVisible();
  await expect(page.locator('.historical')).toContainText('LaLiga 2015/16');
  await expect(page.locator('.visual-hero cs-pitch')).toBeVisible();
  await expect(page.getByRole('heading',{name:'Partidos analizados'})).toBeVisible();
  await expect(page.locator('.matches-summary li')).toHaveCount(8);
  await expectOldestFirst(page,'.matches-summary li',oldestFirst);
  const oldest=window[window.length-1];
  await expect(page.locator('.matches-summary .score').first()).toContainText(`${oldest.home_score} : ${oldest.away_score}`);
  await expect(page.locator('img[src="/media/clubs/217.png"]').first()).toBeVisible();
  await expect.poll(()=>page.locator('img[src="/media/clubs/217.png"]').first().evaluate(image=>(image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await expect(page.locator('img[src="/media/players/5503.webp"]')).toBeVisible();
  await expect(page.getByRole('button',{name:'Descargar hoja de preparación'})).toHaveCount(0);
  await coachText(page);
  await page.screenshot({path:'test-results/summary-visual-desktop.png',fullPage:true});

  await page.getByRole('link',{name:'Mapa de córners'}).click();
  await expect(page.locator('.map-stage cs-pitch')).toBeVisible();
  expect(await page.locator('.map-stage .pitch-mark').count()).toBeGreaterThan(0);
  await page.getByRole('button',{name:'Mapa de calor'}).click();
  await expect(page.locator('.heat-legend strong')).toContainText('envíos directos representados');
  await page.screenshot({path:'test-results/map-heat-desktop.png',fullPage:true});
  const runId=page.url().split('/')[4];
  const heat=await page.request.get(`http://127.0.0.1:8001/api/v1/scouting-runs/${runId}/destination-heatmap`);
  const data=await heat.json();
  expect(data.cells.reduce((sum:number,cell:{count:number})=>sum+cell.count,0)).toBe(data.included);
  await expect(page.locator('.heat-explanation')).not.toHaveAttribute('open');
  await page.getByText('Cómo leer los colores',{exact:true}).click();
  await expect(page.locator('.heat-explanation')).toContainText('conteos por cuadrícula');
  await expect(page.locator('.heat-legend')).toContainText('El color se ajusta a los filtros seleccionados');
  await expect(page.locator('.heat-scale')).toContainText('por cuadrícula');
  const sortedZones=[...data.zones].sort((a:{count:number},b:{count:number})=>b.count-a.count);
  expect(await page.locator('.heat-zone strong').allTextContents()).toEqual(sortedZones.map((zone:{count:number})=>String(zone.count)));
  expect(await page.locator('.heat-zone progress').evaluateAll(nodes=>nodes.map(node=>(node as HTMLProgressElement).max))).toEqual(sortedZones.map(()=>data.included));
  await expect(page.locator('.heat-exclusions li').first()).toContainText(String(data.excluded_non_direct));
  await expect(page.locator('.heat-exclusions li').last()).toContainText(String(data.excluded_spatial));
  await page.getByText('Cómo leer los colores',{exact:true}).click();
  await expect(page.locator('.heat-cell')).toHaveCount(data.cells.filter((cell:{count:number})=>cell.count>0).length);
  await expect(page.locator('.heat-hit')).toHaveCount(data.cells.filter((cell:{count:number})=>cell.count>0).length);
  const peakTitle=page.locator('.heat-hit title').filter({hasText:`${data.max_count} de ${data.included} destinos directos`}).first();
  await expect(peakTitle).toHaveCount(1);
  expect(await page.locator('.heat-stage svg').evaluate(svg=>{
    const layer=svg.querySelector('.heat-layer');
    const lines=svg.querySelector('.pitch-lines');
    return !!layer&&!!lines&&!!(layer.compareDocumentPosition(lines)&Node.DOCUMENT_POSITION_FOLLOWING);
  })).toBe(true);
  await page.getByRole('combobox',{name:'Lado',exact:true}).selectOption('y_bajo');
  const left=await page.request.get(`http://127.0.0.1:8001/api/v1/scouting-runs/${runId}/destination-heatmap?side=y_bajo`);
  const leftData=await left.json();
  await expect(page.locator('.heat-legend strong')).toContainText(`${leftData.included} envíos`);
  await page.getByLabel('Ejecución').selectOption('corto');
  await expect(page.getByText(/Para ver pases en corto/)).toBeVisible();
  await expect(page.locator('.heat-cell')).toHaveCount(0);
  await expect(page.locator('.heat-legend')).toContainText('Sin destinos para representar');
  await page.getByRole('button',{name:'Pases',exact:true}).click();
  await coachText(page);

  await page.getByRole('link',{name:'Patrones'}).click();
  await expect(page.getByRole('heading',{name:'Patrones de envío'})).toBeVisible();
  await expect(page.locator('.pattern-panel cs-pitch').first()).toBeVisible();
  await page.screenshot({path:'test-results/patterns-visual-desktop.png',fullPage:true});
  await expect(page.locator('.pattern-gallery')).not.toContainText('Envíos hacia zona');
  await expect(page.locator('.sample-note').first()).toContainText('destinos similares');
  await page.getByLabel('Mostrar pases desde').selectOption('y_bajo');
  for(const panel of await page.locator('.pattern-panel').all()){
    const points=await panel.locator('.pitch-mark').count();
    await expect(panel.locator('.pattern-top .eyebrow')).toContainText(`Apareció ${points}`);
    expect(points).toBeGreaterThan(0);
  }
  await expect(page.locator('cs-zone-guide')).toHaveCount(0);
  await page.getByLabel('Mostrar pases desde').selectOption('');
  await page.getByRole('link',{name:'Resumen',exact:true}).click();
  await expect(page.locator('.summary-destinations .destination-row')).toHaveCount(4);
  const centralZone=page.locator('.destination-row[data-zone="franja_central"]');
  await centralZone.click();
  await expect(centralZone).toHaveAttribute('aria-pressed','true');
  const zoneCount=Number((await centralZone.locator('strong').innerText()).match(/\d+/)?.[0]);
  await expect(page.locator('.summary-destinations .zone-highlighted')).toHaveCount(zoneCount);
  await centralZone.click();
  await expect(centralZone).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('.summary-destinations .zone-highlighted')).toHaveCount(0);
  await expect(page.locator('cs-zone-guide')).toHaveCount(1);
  await page.getByText('Cómo leer las zonas',{exact:true}).click();
  await expect(page.locator('.summary-destinations cs-zone-guide svg')).toBeVisible();
  await page.getByRole('link',{name:'Patrones',exact:true}).click();
  await coachText(page);
  await page.getByRole('link',{name:'Reporte táctico'}).click();
  await expect(page.getByRole('heading',{name:'Reporte táctico'})).toBeVisible();
  await expect(page.locator('.report-hero cs-pitch')).toBeVisible();
  await expect(page.locator('.report-review')).toContainText('Para revisar en vídeo');
  await expect(page.locator('.report-hero')).not.toContainText('Pregunta para el equipo');
  await expect(page.locator('.report-facts')).toContainText('Tiro tras el córner');
  const shotHelp=page.locator('cs-shot-explanation summary');
  await shotHelp.focus();
  await shotHelp.press('Enter');
  await expect(page.locator('.shot-steps li')).toHaveCount(3);
  await expect(page.locator('.shot-rule')).toContainText(['El equipo pierde la posesión','Justo a los 15 segundos también cuenta']);
  await expect(page.locator('cs-shot-explanation')).toContainText('SCR-15');
  await shotHelp.press('Enter');
  await expect(page.locator('.shot-help')).not.toHaveAttribute('open');
  await page.screenshot({path:'test-results/report-visual-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Generar lectura táctica'}).click();
  await expect(page.getByText('Redactada con plantilla determinista', {exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Ver todas las observaciones',exact:true}).click();
  await expect(page.locator('.report-claims > div').first().locator('li')).toHaveCount(6);
  await page.getByRole('button',{name:'Ver menos',exact:true}).click();
  await expect(page.locator('.report-claims > div').first().locator('li')).toHaveCount(3);
  await expect(page.getByRole('heading',{name:'Qué vimos',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Qué revisar en vídeo',exact:true})).toBeVisible();
  await coachText(page);
  await page.getByRole('link',{name:'Calidad'}).click();
  await expect(page.getByRole('heading',{name:'¿Cuánto peso dar a estos hallazgos?'})).toBeVisible();
  await expect(page.locator('.quality-match')).toHaveCount(8);
  await expectOldestFirst(page,'.quality-match',oldestFirst);
  await expect(page.locator('.quality-match progress')).toHaveCount(8);
  await expect(page.locator('.quality-fixture').first().locator('img')).toHaveCount(2);
  await expect(page.locator('.quality-fixture').first()).not.toContainText('Barcelona');
  await expect(page.getByText('Modelo: Tasa histórica de la liga')).toBeVisible();
  await expect(page.getByText('Modelo: Regresión logística')).toBeVisible();
  await expect(page.getByText('Modelo: Regresión de Poisson')).toBeVisible();
  await expect(page.getByText('Sin predicción',{exact:true})).toBeVisible();
  await coachText(page);
  await page.getByRole('link',{name:'Asistente de evidencia'}).click();
  await page.getByRole('button',{name:'¿Qué partidos se analizaron?'}).click();
  await page.getByRole('button',{name:'Consultar evidencia'}).click();
  await expect(page.locator('.agent-answer li')).toHaveCount(8);
  await expect(page.locator('.agent-answer')).toContainText('Barcelona vs. Sevilla');
  await page.getByRole('button',{name:'¿Cuántos córners generaron un tiro en los siguientes 15 segundos?'}).click();
  await page.getByRole('button',{name:'Consultar evidencia'}).click();
  await expect(page.locator('.agent-answer strong').first()).toContainText('córners evaluables');
  await expect(page.locator('.agent-answer')).toContainText('Sobre la predicción');
  await coachText(page);
  expect(errors).toEqual([]);
});

test('missing history does not create an incomplete analysis',async({page})=>{
  await page.goto('/analysis/new');
  await page.getByLabel('Cómo elegir la muestra').selectOption('date');
  await page.getByLabel('Fecha de corte (exclusiva)').fill('2015-08-01');
  await page.getByRole('button',{name:'Ver ocho partidos anteriores'}).click();
  await expect(page.getByText('Datos insuficientes: 0 de 8 partidos anteriores al corte.')).toBeVisible();
  await expect(page.getByRole('button',{name:'Crear análisis'})).toHaveCount(0);
  await page.getByLabel('Cómo elegir la muestra').selectOption('match');
  await page.getByRole('combobox',{name:'Partido objetivo'}).selectOption({index:1});
  await page.getByRole('button',{name:'Ver ocho partidos anteriores'}).click();
  await expect(page.locator('ol.matches li')).toHaveCount(8);
  await page.getByRole('button',{name:'Crear análisis'}).click();
  await expect(page.getByRole('heading',{name:'¿Qué debemos preparar?'})).toBeVisible();
});

test('six mobile tabs, dark mode, errors and reduced motion',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/');
  await page.getByRole('button',{name:'Activar modo oscuro'}).click();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.getByRole('link',{name:'Preparar un análisis'}).click();
  await page.getByRole('combobox',{name:'Partido objetivo'}).selectOption({index:1});
  await page.getByRole('button',{name:'Ver ocho partidos anteriores'}).click();
  await page.getByRole('button',{name:'Crear análisis'}).click();
  const tabs=page.getByRole('navigation',{name:'Secciones del análisis'}).getByRole('link');
  await expect(tabs).toHaveCount(6);
  await expect(page.getByRole('heading',{name:'¿Qué debemos preparar?'})).toBeVisible();
  for(const tab of await tabs.all())await expect(tab).toBeInViewport();
  await expect(page.locator('.visual-hero cs-pitch')).toBeVisible();
  await expect(page.locator('.matches-summary li')).toHaveCount(8);
  expect(await page.locator('.pitch-mark').first().evaluate(el=>getComputedStyle(el).animationName)).toBe('none');
  await page.screenshot({path:'test-results/summary-visual-mobile-dark.png',fullPage:true});
  await page.locator('cs-shot-explanation summary').click();
  await expect(page.locator('.shot-rule').last()).toContainText('fuera del porcentaje');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({path:'test-results/shot-help-mobile-dark.png',fullPage:true});
  await page.locator('cs-shot-explanation summary').click();
  await page.getByRole('link',{name:'Calidad'}).click();
  await expect(page.locator('.quality-match')).toHaveCount(8);
  await expect(page.locator('.quality-fixture').first().locator('img')).toHaveCount(2);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByRole('link',{name:'Mapa de córners'}).click();
  await page.route('**/destination-heatmap*',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'canonical_contract_hash_mismatch'})}));
  await page.getByRole('button',{name:'Mapa de calor'}).click();
  await expect(page.getByRole('alert').getByText(/No pudimos mostrar estos destinos/)).toBeVisible();
  await coachText(page);
  await page.unroute('**/destination-heatmap*');
  await page.getByRole('button',{name:'Reintentar'}).click();
  await expect(page.locator('.heat-legend strong')).toContainText('envíos directos representados');
  await page.screenshot({path:'test-results/map-mobile-dark.png',fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByRole('button',{name:'Activar modo claro'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
});

test('all 20 badges and 202 taker portraits ship with the client',async({page})=>{
  expect(Object.keys(clubNames)).toHaveLength(20);
  expect(Object.keys(userTakerPhotos)).toHaveLength(75);
  for(const id of Object.keys(clubNames)){
    const badge=await page.request.get(`/media/clubs/${id}.png`);
    expect(badge.ok(),`club ${id} image missing`).toBeTruthy();
  }
  const newPortrait=await page.request.get('/media/players/6671.webp');
  expect(newPortrait.ok()).toBeTruthy();
  await page.goto('/analysis/new');
  await page.getByLabel('Equipo rival').selectOption('Athletic Club');
  await page.getByLabel('Cómo elegir la muestra').selectOption('date');
  await page.getByLabel('Fecha de corte (exclusiva)').fill('2016-03-01');
  await page.getByRole('button',{name:'Ver ocho partidos anteriores'}).click();
  await page.getByRole('button',{name:'Crear análisis'}).click();
  await expect(page.locator('img[src="/media/players/6396.webp"]')).toBeVisible();
  await expect(page.locator('.matches-summary img[src^="/media/clubs/"]').first()).toBeVisible();
  await page.getByRole('link',{name:'Calidad'}).click();
  await coachText(page);
  await page.getByRole('link',{name:'Créditos de imágenes'}).click();
  await expect(page.getByRole('heading',{name:'Créditos de imágenes'})).toBeVisible();
});
