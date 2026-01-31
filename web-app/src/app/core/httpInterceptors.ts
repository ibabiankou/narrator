import { HttpContextToken, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError, timeout, TimeoutError } from 'rxjs';

export const HTTP_TIMEOUT_MS = new HttpContextToken<number>(() => 1000);

/**
 * Adds timeout to all requests. The default value is 1s. Set to 0 to disable it.
 *
 * ```ts
 * // Set longer timeout for this request
 * this.http.get('/api/slow-endpoint', {
 *   context: new HttpContext().set(HTTP_TIMEOUT_MS, 10_000)
 * }).subscribe();
 *
 * // Disable timeout
 * this.http.get('/api/unpredictable-endpoint', {
 *   context: new HttpContext().set(HTTP_TIMEOUT_MS, 0)
 * }).subscribe();
 * ```
 */
export const timeoutInterceptor: HttpInterceptorFn = (req, next) => {
  const timeoutMs = req.context.get(HTTP_TIMEOUT_MS);
  if (timeoutMs <= 0) {
    return next(req);
  } else {
    return next(req).pipe(
      timeout(timeoutMs),
      catchError(err => {
        if (err instanceof TimeoutError) {
          console.error('Request timed out!');
        }
        return throwError(() => err);
      })
    );
  }
};
