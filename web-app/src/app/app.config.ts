import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection
} from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';

import { routes } from './app.routes';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideServiceWorker } from '@angular/service-worker';
import { timeoutInterceptor } from './core/httpInterceptors';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(
      withInterceptors([timeoutInterceptor])
    ),
    provideServiceWorker('ngsw-worker.js', {
      enabled: true,
      registrationStrategy: 'registerWhenStable:30000'
    })
  ]
};
