import { test, expect } from '@playwright/test';

test('real data: eight matches, dashboard, map, patterns, report and quality',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 await page.getByRole('link',{name:'Preparar un análisis'}).click();
 await expect(page.getByLabel('Equipo rival')).toHaveValue('Barcelona');
 await page.getByRole('button',{name:'Ver ocho partidos anteriores'}).click();
 await expect(page.locator('ol.matches li')).toHaveCount(8);
 await page.getByRole('button',{name:'Confirmar y analizar'}).click();
 await expect(page.getByText('SCR-15 OBSERVADO',{exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Barcelona',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Mapa de córners'}).click();
 await expect(page.locator('svg.pitch')).toBeVisible();
 expect(await page.locator('svg.pitch line').count()).toBeGreaterThan(0);
 await page.getByRole('combobox',{name:'Envío',exact:true}).selectOption('corto');
 await page.getByRole('link',{name:'Patrones',exact:true}).click();
 await expect(page.getByText('PATRÓN',{exact:false}).first()).toBeVisible();
 await page.getByRole('link',{name:'Reporte táctico',exact:true}).click();
 await expect(page.getByText('Plan de ejecución antes de generar:')).toBeVisible();
 await page.getByRole('button',{name:'Generar reporte táctico',exact:true}).click();
 await expect(page.getByText('PLANTILLA DETERMINISTA',{exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Calidad',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Calidad y trazabilidad'})).toBeVisible();
 expect(errors).toEqual([]);
 await page.screenshot({path:'test-results/quality.png',fullPage:true});
});

test('insufficient history and target-match selection',async({page})=>{
 await page.goto('/analysis/new');
 await expect(page.getByLabel('Equipo rival')).toHaveValue('Barcelona');
 await page.getByLabel('Fecha de corte (exclusiva)').fill('2015-08-01');
 await page.getByRole('button',{name:'Ver ocho partidos anteriores'}).click();
 await expect(page.getByText('Datos insuficientes: 0 de 8 partidos anteriores al corte.')).toBeVisible();
 await expect(page.getByRole('button',{name:'Confirmar y analizar'})).toHaveCount(0);
 await page.getByLabel('Tipo de corte').selectOption('match');
 const option=page.getByRole('combobox',{name:'Partido objetivo',exact:true}).locator('option').nth(1);
 await expect(option).toBeAttached();
 await page.getByRole('combobox',{name:'Partido objetivo',exact:true}).selectOption({index:1});
 await page.getByRole('button',{name:'Ver ocho partidos anteriores'}).click();
 await expect(page.locator('ol.matches li')).toHaveCount(8);
 await page.getByRole('button',{name:'Confirmar y analizar'}).click();
 await expect(page.getByText('SCR-15 OBSERVADO',{exact:true})).toBeVisible();
});
