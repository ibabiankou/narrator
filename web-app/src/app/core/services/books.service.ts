import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { catchError, map, Observable, of, switchMap, tap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { BookOverview, BookWithContent, CreateBookRequest, PlaybackInfo } from '../models/books.dto';
import { IndexDBCache } from './indexDBCache';
import { ConnectionService } from './connection.service';
import { PageResponse, toPageResponse } from '../models/pagination.dto';

@Injectable({
  providedIn: 'root'
})
export class BooksService {

  private apiUrl = `${environment.api_base_url}/books`;
  private playbackInfoCache: IndexDBCache<PlaybackInfo>;
  private booksCache: IndexDBCache<BookWithContent>;

  constructor(private http: HttpClient,
              private connectionService: ConnectionService) {
    this.playbackInfoCache = new IndexDBCache(
      this.connectionService,
      "playback-info",
      (url: string) => this.http.get<PlaybackInfo>(url),
      (url: string, info: PlaybackInfo) => this.http.post<void>(url, info));
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
            page.file_url = `${environment.api_base_url}/files/${bookId}/pages/${page.file_name}`
          });
        }));
  }

  listBooks(page: number = 1, size: number = 10): Observable<PageResponse<BookOverview>> {
    const loadFromCache =
      this.booksCache.getAll().pipe(
        map(bwc => bwc.map(bwc => bwc.overview)),
        map(overviews => toPageResponse(overviews, page, size)),
      );

    var params = new HttpParams();
    params = params.append('page', page);
    params = params.append('size', size);
    const loadFromApi =
      this.http.get<PageResponse<BookOverview>>(`${this.apiUrl}/`, {params: params}).pipe(
        // Fall back to cache in case of error? Might be frustrating, if its a genuine API error...
        catchError(() => loadFromCache)
      );

    return this.connectionService.isOnline() ? loadFromApi : loadFromCache;
  }

  searchBooks(query: string, page: number = 1, size: number = 10): Observable<PageResponse<BookOverview>> {
    var params = new HttpParams();
    params = params.append('query', query);
    params = params.append('page', page);
    params = params.append('size', size);
    return this.http.get<PageResponse<BookOverview>>(`${this.apiUrl}/search`, {params: params});
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

  getPlaylistUrl(id: string) {
    return `${environment.api_base_url}/books/${id}/m3u8`;
  }
}
