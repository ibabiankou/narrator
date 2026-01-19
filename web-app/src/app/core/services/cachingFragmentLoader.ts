import Hls, {
  FragmentLoaderContext,
  HlsConfig,
  Loader,
  LoaderCallbacks,
  LoaderConfiguration,
  LoaderContext, LoaderOnSuccess, LoaderResponse,
  LoaderStats, LoadStats,
} from 'hls.js';
import { IndexDBCache } from './indexDBCache';
import { ConnectionService } from './connection.service';

export class CachingFragmentLoader implements Loader<FragmentLoaderContext> {
  private loader: Loader<LoaderContext>;
  stats: LoaderStats;
  context!: FragmentLoaderContext;

  private cache: IndexDBCache<LoaderResponse>;

  constructor(config: HlsConfig) {
    this.loader = new Hls.DefaultConfig.loader(config);
    this.stats = new LoadStats();
    this.cache = new IndexDBCache(
      new ConnectionService(),
      "fragments");
  }

  load(context: FragmentLoaderContext, config: LoaderConfiguration, callbacks: LoaderCallbacks<FragmentLoaderContext>): void {
    this.context = context;
    const cachingOnSuccess: LoaderOnSuccess<FragmentLoaderContext> =
      (response: LoaderResponse, stats: LoaderStats, context: FragmentLoaderContext, networkDetails: any) => {
        this.cache.set(context.url, response).subscribe();
        callbacks.onSuccess(response, stats, context, networkDetails)
      };
    const modifiedCallbacks: LoaderCallbacks<FragmentLoaderContext> = {
      "onSuccess": cachingOnSuccess,
      "onError": callbacks.onError,
      "onTimeout": callbacks.onTimeout,
      "onAbort": callbacks.onAbort,
      "onProgress": callbacks.onProgress
    };

    this.cache.get(context.url)
      .subscribe(entry => {
        if (entry) {
          callbacks.onSuccess(entry, this.stats, context, null);
        } else {
          this.loader.load(context, config, <LoaderCallbacks<LoaderContext>>modifiedCallbacks);
        }
      });
  }

  abort(): void {
    this.loader.abort();
  }

  destroy(): void {
    this.loader.destroy();
  }
}
