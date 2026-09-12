import { Routes } from '@angular/router';
export const routes: Routes = [
 {path:'',loadComponent:()=>import('./features/home').then(m=>m.Home)},
 {path:'analysis/new',loadComponent:()=>import('./features/setup').then(m=>m.Setup)},
 {path:'analysis/:id/:view',loadComponent:()=>import('./features/analysis').then(m=>m.Analysis)},
 {path:'analysis/:id',redirectTo:'analysis/:id/summary',pathMatch:'full'},
 {path:'**',redirectTo:''}
];
