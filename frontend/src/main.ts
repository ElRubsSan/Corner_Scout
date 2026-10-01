import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { App } from './app/app';
import { routes } from './app/routes';
bootstrapApplication(App, { providers: [provideRouter(routes, withInMemoryScrolling({scrollPositionRestoration:'top'}))] }).catch(console.error);
