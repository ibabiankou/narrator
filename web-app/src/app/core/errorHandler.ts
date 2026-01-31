import { ErrorHandler, Injectable } from '@angular/core';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  handleError(error: any): void {
    const errorLog = {
      message: error.message || error.toString(),
      stack: error.stack || '',
      time: new Date().toISOString(),
      url: window.location.href
    };

    // Store in localStorage immediately!
    // We don't send to API here because the app might be about to die.
    const logs = JSON.parse(localStorage.getItem('app_errors') || '[]');
    logs.push(errorLog);
    localStorage.setItem('app_errors', JSON.stringify(logs.slice(-10))); // Keep last 10

    console.error('Captured Error:', error);
  }
}
