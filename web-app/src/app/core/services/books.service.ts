import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, forkJoin, map, Observable, of, switchMap, take, tap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { BookOverview, BookWithContent, CreateBookRequest, PlaybackInfo } from '../models/books.dto';
import { DomSanitizer } from '@angular/platform-browser';
import { IndexDBCache } from './indexDBCache';
import { ConnectionService } from './connection.service';

@Injectable({
  providedIn: 'root'
})
export class BooksService {

  private apiUrl = `${environment.api_base_url}/books`;
  private playbackInfoCache: IndexDBCache<PlaybackInfo>;
  private booksCache: IndexDBCache<BookWithContent>;

  constructor(private http: HttpClient,
              private sanitizer: DomSanitizer,
              private connectionService: ConnectionService) {
    this.playbackInfoCache = new IndexDBCache(
      this.connectionService,
      "playback-info",
      (url: string) => this.http.get<PlaybackInfo>(url),
      (url: string, info: PlaybackInfo) => this.http.post<void>(url, info));
    this.playbackInfoCache.onOnlineChange((online) => {
      if (online) {
        this.playbackInfoCache.getAllEntries().then(entries => {
          const syncEntries = entries.filter(entry => entry.syncWhenOnline);

          if (syncEntries.length === 0) {
            return;
          }

          const observables: Observable<void>[] = [];
          for (const entry of syncEntries) {
            observables.push(this.playbackInfoCache.set(entry.url, entry.value));
          }

          return firstValueFrom(forkJoin(observables));
        }).catch(reason => console.warn("Failed to sync some entries:", reason));
      }
    })
    this.booksCache = new IndexDBCache(
      this.connectionService,
      "books",
      (url: string) => this.http.get<BookWithContent>(url));
  }

  createBook(data: CreateBookRequest): Observable<BookOverview> {
    return this.http.post<BookOverview>(`${this.apiUrl}/`, data);
  }

  getBookWithContent(bookId: string): Observable<BookWithContent> {
    const url = `${this.apiUrl}/${bookId}`;
    return this.booksCache.get(url)
      .pipe(
        switchMap(bookMaybe =>
          bookMaybe ? of(bookMaybe) : throwError(() => new Error('Unable to load the book'))),
        tap(bookWithContent => {
          bookWithContent.pages.forEach(page => {
            const url = `${environment.api_base_url}/files/${bookId}/pages/${page.file_name}#toolbar=0&navpanes=0&scrollbar=0`
            page.file_url = this.sanitizer.bypassSecurityTrustResourceUrl(url);
          });
        }));
  }

  listBooks(): Observable<BookOverview[]> {
    return this.connectionService.$isOnline.pipe(
      take(1),
      switchMap(online => online ?
        this.http.get<BookOverview[]>(`${this.apiUrl}/`) :
        this.booksCache.getAll().pipe(map(bwc => bwc.map(bwc => bwc.overview))))
    );
  }

  delete(id: string) {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }

  getPlaybackInfo(bookId: string) {
    return this.playbackInfoCache.get(`${this.apiUrl}/${bookId}/playback_info`);
  }

  updatePlaybackInfo(progress: PlaybackInfo) {
    return this.playbackInfoCache.set(`${this.apiUrl}/${progress.book_id}/playback_info`, progress);
  }
}
