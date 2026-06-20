import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { config } from 'rxjs';
import { GlobalErrorHandler } from './app/core/errorHandler';

// Configure global RxJS unhandled error logging
config.onUnhandledError = (err) => {
  GlobalErrorHandler.handleError(err);
  console.warn('Unhandled RxJS error:', err);
};

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
