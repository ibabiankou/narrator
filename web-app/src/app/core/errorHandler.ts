import { ErrorHandler, Injectable } from '@angular/core';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  handleError(error: any): void {
    // Extract the raw message if it's wrapped in an ErrorEvent or Error object
    const message = error?.message || error?.toString() || '';

    // Suppress the harmless ResizeObserver loop warning
    if (message.includes('ResizeObserver loop completed with undelivered notifications') ||
      message.includes('ResizeObserver loop limit exceeded')) {
      return;
    }

    const errorLog = {
      message: message,
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
