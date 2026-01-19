import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { BookOverview, BookWithContent, CreateBookRequest, PlaybackInfo } from '../models/books.dto';
import { DomSanitizer } from '@angular/platform-browser';
import { BackgroundSyncCache } from './background.sync.cache';
import { ConnectionService } from './connection.service';

@Injectable({
  providedIn: 'root'
})
export class BooksService {

  private apiUrl = `${environment.api_base_url}/books`;
  private playbackInfoCache: BackgroundSyncCache<PlaybackInfo>;

  constructor(private http: HttpClient,
              private sanitizer: DomSanitizer,
              private connectionService: ConnectionService) {
    this.playbackInfoCache = new BackgroundSyncCache(
      this.connectionService,
      "playback-info",
      (url: string) => this.http.get<PlaybackInfo>(url),
      (url: string, info: PlaybackInfo) => this.http.post<void>(url, info)
    );
  }

  createBook(data: CreateBookRequest): Observable<BookOverview> {
    return this.http.post<BookOverview>(`${this.apiUrl}/`, data);
  }

  getBookWithContent(bookId: string): Observable<BookWithContent> {
    const url = `${this.apiUrl}/${bookId}`;
    return this.http.get<BookWithContent>(url).pipe(tap(bookWithContent => {
      bookWithContent.pages.forEach(page => {
        const url = `${environment.api_base_url}/files/${bookId}/pages/${page.file_name}#toolbar=0&navpanes=0&scrollbar=0`
        page.file_url = this.sanitizer.bypassSecurityTrustResourceUrl(url);
      });
    }));
  }

  listBooks(): Observable<BookOverview[]> {
    return this.http.get<BookOverview[]>(`${this.apiUrl}/`);
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
