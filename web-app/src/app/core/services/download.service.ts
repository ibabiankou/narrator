import { inject, Injectable } from '@angular/core';
import { EMPTY, mergeMap, Observable, sampleTime, switchMap, tap } from 'rxjs';
import { BooksService } from './books.service';
import Hls, { Events, LevelLoadedData } from 'hls.js';
import { CachingHlsLoader } from './cachingHlsLoader';
import { FilesService } from './files.service';
import { IndexDBCache } from './indexDBCache';
import { DownloadInfo } from '../models/books.dto';
import { ConnectionService } from './connection.service';

@Injectable({
  providedIn: 'root'
})
export class DownloadService {
  private bookService = inject(BooksService);
  private fileService = inject(FilesService);

  private cache: IndexDBCache<DownloadInfo>;

  constructor(private connectionService: ConnectionService) {
    this.cache = new IndexDBCache(
      this.connectionService,
      "download-info",
    );
  }

  downloadBook(bookId: string) {
    // TODO: Load all pages. Also need to figure out how to display pdf page from cache.

    const downloadInfo: DownloadInfo = {
      id: bookId,
      fragments_total: 0,
      fragments_downloaded: 0,
    };
    this.cache.set(bookId, downloadInfo).subscribe();

    return this.bookService.getBookWithContent(bookId)
      .pipe(
        switchMap((_) =>
          this.getFragmentUrls(this.bookService.getPlaylistUrl(bookId))
            .pipe(tap(urls => {
                downloadInfo.fragments_total = urls.length;
                this.cache.set(bookId, downloadInfo).subscribe();
              })
            )
        ),
        mergeMap(urls => urls),
        mergeMap(url => {
          return this.fileService.isCached(url).pipe(
            switchMap(cached => {
                if (cached) {
                  downloadInfo.fragments_downloaded++;
                  return EMPTY;
                } else {
                  return this.fileService.getFileData(url).pipe(tap(() => downloadInfo.fragments_downloaded++));
                }
              }
            )
          );
        }, 5),
        sampleTime(250),
        tap({
          next: () => this.cache.set(bookId, downloadInfo).subscribe(),
          complete: () => this.cache.set(bookId, downloadInfo).subscribe()
        }),
      );
  }

  private getFragmentUrls(playlistUrl: string) {
    return new Observable<string[]>(subscriber => {
      const hls = new Hls({
        loader: CachingHlsLoader,
        debug: false,
      });
      // TODO: Need to change to something more generic in order to support multiple audio streams.
      hls.on(Hls.Events.LEVEL_LOADED, (event: Events.LEVEL_LOADED, data: LevelLoadedData) => {
        subscriber.next(data.details.fragments.map(fragment => fragment.url));
        subscriber.complete();
      });
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          subscriber.error(data.error);
        }
      });
      hls.loadSource(playlistUrl);
    });
  }

  getDownloadInfo(bookId: string) {
    return this.cache.get(bookId);
  }

  deleteBookData(bookId: string) {
    this.getFragmentUrls(this.bookService.getPlaylistUrl(bookId))
      .pipe(
        mergeMap(urls => urls),
        mergeMap(url => this.fileService.deleteFromCache(url), 1),
      ).subscribe({error: (err) => console.error(err)});
    this.cache.delete(bookId).subscribe();
  }
}
