import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { catchError, map, Observable, of, switchMap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  BookDetails,
  BookMetadata,
  BookMetadataForReview,
  BookOverview,
  PlaybackInfo,
  TocItem
} from '../models/books.dto';
import { IndexDBCache } from './indexDBCache';
import { ConnectionService } from './connection.service';
import { DEFAULT_PAGE_SIZE, PageResponse, toPageResponse } from '../models/pagination.dto';

@Injectable({
  providedIn: 'root'
})
export class BooksService {

  private apiUrl = `${environment.api_base_url}/books`;
  private playbackInfoCache: IndexDBCache<PlaybackInfo>;
  private bookDetailsCache: IndexDBCache<BookDetails>;

  constructor(private http: HttpClient,
              private connectionService: ConnectionService) {
    this.playbackInfoCache = new IndexDBCache(
      this.connectionService,
      "playback-info",
      (url: string) => this.http.get<PlaybackInfo>(url),
      (url: string, info: PlaybackInfo) => this.http.post<void>(url, info));
    this.bookDetailsCache = new IndexDBCache(
      this.connectionService,
      "book-details",
      (url: string) => this.http.get<BookDetails>(url));

    // TODO: drop it at some point.
    indexedDB.deleteDatabase("books");
  }

  getBookDetails(bookId: string): Observable<BookDetails> {
    const url = `${this.apiUrl}/${bookId}/details`;
    return this.bookDetailsCache.get(url)
      .pipe(
        switchMap(bookMaybe =>
          bookMaybe ? of(bookMaybe) : throwError(() => new Error('Unable to load the book details'))),
        );
  }

  listBooks(pageIndex?: number, size?: number): Observable<PageResponse<BookOverview>> {
    const loadFromCache =
      this.bookDetailsCache.getAll().pipe(
        map(overviews => overviews.reverse()),
        map(overviews => toPageResponse(overviews, pageIndex || 0, size || DEFAULT_PAGE_SIZE)),
      );

    let params = new HttpParams();
    if (pageIndex !== undefined) {
      params = params.append('page_index', pageIndex);
    }
    if (size !== undefined) {
      params = params.append('size', size);
    }
    const loadFromApi =
      this.http.get<PageResponse<BookOverview>>(`${this.apiUrl}/`, {params: params}).pipe(
        // Fall back to cache in case of error? Might be frustrating, if its a genuine API error...
        catchError(() => loadFromCache)
      );

    return this.connectionService.isOnline() ? loadFromApi : loadFromCache;
  }

  searchBooks(query: string, pageIndex?: number, size?: number): Observable<PageResponse<BookOverview>> {
    let params = new HttpParams();
    params = params.append('query', query);
    if (pageIndex !== undefined) {
      params = params.append('page_index', pageIndex);
    }
    if (size !== undefined) {
      params = params.append('size', size);
    }
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
    return `${environment.api_base_url}/files/${id}/playlists/master.m3u8`;
  }

  uploadBook(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<BookOverview>(`${this.apiUrl}/`, formData);
  }

  getBookMetadataForReview(bookId: string) {
    return this.http.get<BookMetadataForReview>(`${this.apiUrl}/${bookId}/metadata/review`);
  }

  updateBookMetadata(bookId: string, metadata: BookMetadata) {
    return this.http.post<BookOverview>(`${this.apiUrl}/${bookId}/metadata/review`, metadata);
  }

  uploadCover(bookId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<string>(`${this.apiUrl}/${bookId}/metadata/upload-cover`, formData);
  }

  getTableOfContent(bookId: string) {
    return this.http.get<TocItem[]>(`${this.apiUrl}/${bookId}/table-of-contents`);
  }

  startNarration(bookId: string, tocItems: TocItem[]) {
    return this.http.post<any>(`${this.apiUrl}/${bookId}/narrate`, tocItems);
  }
}
