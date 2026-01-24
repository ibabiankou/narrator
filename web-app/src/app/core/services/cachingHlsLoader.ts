import {
  Loader,
  LoaderCallbacks,
  LoaderConfiguration,
  LoaderContext,
  LoaderResponse,
  LoaderStats,
  LoadStats
} from 'hls.js';
import { FilesService } from './files.service';
import { ServiceLocator } from '../../app';
import { retry, timer } from 'rxjs';

export class CachingHlsLoader implements Loader<LoaderContext> {
  stats: LoaderStats;
  context!: LoaderContext;
  private filesService: FilesService;

  constructor() {
    this.stats = new LoadStats();
    this.filesService = ServiceLocator.injector.get(FilesService);
  }

  load(context: LoaderContext, config: LoaderConfiguration, callbacks: LoaderCallbacks<LoaderContext>): void {
    this.context = context;

    this.filesService.getFileData(context.url)
      .pipe(
        retry({
          count: 30,
          delay: (error, retryCount) => {
            const initialDelay = 1000;
            const maxDelay = 30000;
            const backoffTime = Math.min(Math.pow(2, retryCount - 1) * initialDelay, maxDelay);
            const jitter = (Math.random() * 2 - 1) * (backoffTime * 0.2);
            const finalDelay = backoffTime + jitter;
            return timer(finalDelay);
          }
        })
      )
      .subscribe({
        next: (file) => {
          const response: LoaderResponse = {
            url: file.url,
            data: file.data,
          }
          callbacks.onSuccess(response, this.stats, context, null);
        },
        error: (err) => {
          const error = {code: 504, text: err,};
          callbacks.onError(error, context, null, this.stats);
        }
      });
  }

  abort(): void {
    // No-op
  }

  destroy(): void {
    // No-op
  }
}
