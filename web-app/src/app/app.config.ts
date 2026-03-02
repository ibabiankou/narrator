import {
  ApplicationConfig, ErrorHandler,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection
} from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';

import { routes } from './app.routes';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideServiceWorker } from '@angular/service-worker';
import { timeoutInterceptor } from './core/httpInterceptors';
import { GlobalErrorHandler } from './core/errorHandler';
import { AutoRefreshTokenService, provideKeycloak, UserActivityService, withAutoRefreshToken } from 'keycloak-angular';

export const appConfig: ApplicationConfig = {
  providers: [
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(
      withInterceptors([timeoutInterceptor])
    ),
    provideKeycloak({
      config: {
        url: 'https://iam.nnarrator.eu',
        realm: 'nnarrator',
        clientId: 'nnarrator-webapp'
      },
      initOptions: {
        onLoad: 'check-sso',
        silentCheckSsoRedirectUri: window.location.origin + '/app/sso/silent-check.html',
        pkceMethod: 'S256'
      },
      features: [
        withAutoRefreshToken({
          onInactivityTimeout: "login"
        })
      ],
      providers: [
        AutoRefreshTokenService,
        UserActivityService
      ]
    }),
    provideServiceWorker('ngsw-worker.js', {
      enabled: true,
      registrationStrategy: 'registerWhenStable:30000'
    })
  ]
};
