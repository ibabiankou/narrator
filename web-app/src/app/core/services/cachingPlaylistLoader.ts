import Hls, {
  HlsConfig,
  Loader,
  LoaderCallbacks,
  LoaderConfiguration,
  LoaderContext, LoaderOnSuccess, LoaderResponse,
  LoaderStats, LoadStats,
  PlaylistLoaderContext
} from 'hls.js';
import { IndexDBCache } from './indexDBCache';
import { ConnectionService } from './connection.service';

export class CachingPlaylistLoader implements Loader<PlaylistLoaderContext> {
  private loader: Loader<LoaderContext>;
  stats: LoaderStats;
  context!: PlaylistLoaderContext;

  private cache: IndexDBCache<LoaderResponse>;

  constructor(config: HlsConfig) {
    this.loader = new Hls.DefaultConfig.loader(config);
    this.stats = new LoadStats();
    console.info("Initial stats %s", this.stats);
    this.cache = new IndexDBCache(
      new ConnectionService(),
      "playlists");
  }

  load(context: PlaylistLoaderContext, config: LoaderConfiguration, callbacks: LoaderCallbacks<PlaylistLoaderContext>): void {
    this.context = context;

    const cachingOnSuccess: LoaderOnSuccess<PlaylistLoaderContext> =
      (response: LoaderResponse, stats: LoaderStats, context: PlaylistLoaderContext, networkDetails: any) => {
        // Should I do anything with the subscription?
        console.log("Caching response obtained by loader.onSuccess");
        this.cache.set(context.url, response).subscribe(
          {
            next: () => console.log("Cached response."),
            error: reason => console.warn("Failed to cache response:", reason),
            complete: () => console.log("Cache observable has completed.")
          }
        );
        callbacks.onSuccess(response, stats, context, networkDetails)
      };
    const modifiedCallbacks: LoaderCallbacks<PlaylistLoaderContext> = {
      "onSuccess": cachingOnSuccess,
      "onError": callbacks.onError,
      "onTimeout": callbacks.onTimeout,
      "onAbort": callbacks.onAbort,
      "onProgress": callbacks.onProgress
    };

    this.cache.get(context.url)
      .subscribe(entry => {
        if (entry) {
          console.log("Using cached response.");
          callbacks.onSuccess(entry, this.stats, context, null);
        } else {
          console.log("Calling default loader.");
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
