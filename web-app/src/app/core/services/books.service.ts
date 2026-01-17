import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { BookOverview, BookWithContent, CreateBookRequest } from '../models/books.dto';
import { DomSanitizer } from '@angular/platform-browser';

@Injectable({
  providedIn: 'root'
})
export class BooksService {

  private apiUrl = `${environment.api_base_url}/books`;

  constructor(private http: HttpClient, private sanitizer: DomSanitizer) {
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
}
