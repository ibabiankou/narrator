import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { TempFile } from '../models/files.dto';

@Injectable({
  providedIn: 'root'
})
export class FilesService {

  private apiUrl = `${environment.api_base_url}/files/`;

  constructor(private http: HttpClient) { }

  uploadFile(file: File): Observable<TempFile> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<TempFile>(this.apiUrl, formData);
  }
}
