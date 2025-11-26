import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { BookContent, BookDetails, CreateBookRequest, Playlist } from '../models/books.dto';
import { DomSanitizer } from '@angular/platform-browser';

@Injectable({
  providedIn: 'root'
})
export class BooksService {

  private apiUrl = `${environment.api_base_url}/books`;
  constructor(private http: HttpClient, private sanitizer: DomSanitizer) {
  }

  createBook(data: CreateBookRequest): Observable<BookDetails> {
    return this.http.post<BookDetails>(`${this.apiUrl}/`, data);
  }

  getBook(bookId: string): Observable<BookDetails> {
    const url = `${this.apiUrl}/${bookId}`;
    return this.http.get<BookDetails>(url);
  }

  listBooks(): Observable<BookDetails[]> {
    return this.http.get<BookDetails[]>(`${this.apiUrl}/`);
  }

  getBookContent(bookId: string, lastPageIndex: number = 0, limit: number = 10): Observable<BookContent> {
    const httpParams = new HttpParams({
      fromObject: {
        last_page_idx: lastPageIndex,
        limit: limit
      }
    });
    return this.http.get<BookContent>(`${this.apiUrl}/${bookId}/content`, {params: httpParams})
      .pipe(tap(content => {
        content.pages.forEach(page => {
          const url = `${this.apiUrl}/${bookId}/pages/${page.file_name}#toolbar=0&navpanes=0&scrollbar=0`
          page.file_url = this.sanitizer.bypassSecurityTrustResourceUrl(url);
        });
      }));
  }

  getPlaylist(bookId: string) {
    return this.http.get<Playlist>(`${this.apiUrl}/${bookId}/playlist`);
  }
}
