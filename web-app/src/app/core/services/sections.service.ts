import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { BookContent, BookDetails, CreateBookRequest, Section } from '../models/books.dto';
import { DomSanitizer } from '@angular/platform-browser';

@Injectable({
  providedIn: 'root'
})
export class SectionsService {

  private apiUrl = `${environment.api_base_url}/sections`;
  constructor(private http: HttpClient) {
  }

  updateSection(section: Section) {
    return this.http.post(`${this.apiUrl}/${section.id}`, section);
  }

  deleteSection(sectionId: number) {
    return this.http.delete(`${this.apiUrl}/${sectionId}`);
  }

  generateSpeech(id: number, mode: string) {
    const request = {
      "mode": mode
    }
    return this.http.post(`${this.apiUrl}/${id}/generate-speech`, request);
  }
}
