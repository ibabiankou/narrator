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
import {
  AutoRefreshTokenService,
  createInterceptorCondition, INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG, IncludeBearerTokenCondition,
  includeBearerTokenInterceptor,
  provideKeycloak,
  UserActivityService,
  withAutoRefreshToken
} from 'keycloak-angular';
import { environment } from '../environments/environment';

const urlCondition = createInterceptorCondition<IncludeBearerTokenCondition>({
  urlPattern: environment.auth_url_pattern
});

export const appConfig: ApplicationConfig = {
  providers: [
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(
      withInterceptors([timeoutInterceptor, includeBearerTokenInterceptor])
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
          onInactivityTimeout: "login",
          loginOptions: {
            prompt: "none",
          }
        })
      ],
      providers: [
        AutoRefreshTokenService,
        UserActivityService
      ]
    }),
    {
      provide: INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
      useValue: [urlCondition]
    },
    provideServiceWorker('ngsw-worker.js', {
      enabled: true,
      registrationStrategy: 'registerWhenStable:30000'
    })
  ]
};
