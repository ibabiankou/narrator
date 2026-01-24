import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { EMPTY, firstValueFrom, forkJoin, map, Observable, switchMap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { TempFile } from '../models/files.dto';
import { IndexDBCache } from './indexDBCache';
import { ConnectionService } from './connection.service';
import { BooksService } from './books.service';
import Hls, { Events, LevelLoadedData } from 'hls.js';
import { CachingHlsLoader } from './cachingHlsLoader';
import { FilesService } from './files.service';

@Injectable({
  providedIn: 'root'
})
export class DownloadService {
  private bookService = inject(BooksService);
  private fileService = inject(FilesService);


  downloadBook(bookId: string) {
    // TODO: Load all pages. Also need to figure out how to display pdf page from cache.

    this.bookService.getBookWithContent(bookId)
      .pipe(
        switchMap((_) => {
          return this.getFragmentUrls(this.bookService.getPlaylistUrl(bookId));
        }),
        switchMap(urls => {
          console.log("Loading %s fragments", urls.length);
          if (urls.length == 0) {
            return EMPTY;
          }
          const observables: Observable<any>[] = [];
          urls.forEach(url => observables.push(this.fileService.getFileData(url)));
          return firstValueFrom(forkJoin(observables));
        })
      ).subscribe();
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

}
