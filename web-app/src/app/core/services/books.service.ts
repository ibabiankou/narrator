import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { BookDetails, CreateBookRequest } from '../models/books.dto';

@Injectable({
  providedIn: 'root'
})
export class BooksService {

  private apiUrl = `${environment.api_base_url}/books`;

  constructor(private http: HttpClient) {
  }

  createBook(data: CreateBookRequest): Observable<BookDetails> {
    return this.http.post<BookDetails>(`${this.apiUrl}/`, data);
  }

  getBook(bookId: string): Observable<BookDetails> {
    return this.http.get<BookDetails>(`${this.apiUrl}${bookId}/`);
  }
}
