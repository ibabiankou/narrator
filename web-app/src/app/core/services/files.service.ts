import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable, switchMap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { TempFile } from '../models/files.dto';
import { IndexDBCache } from './indexDBCache';
import { ConnectionService } from './connection.service';

interface FileData {
  url: string;
  data: string | ArrayBuffer | Object;
  headers: Record<string, string>;
}

@Injectable({
  providedIn: 'root'
})
export class FilesService {

  private apiUrl = `${environment.api_base_url}/files/`;
  private cache: IndexDBCache<FileData>;

  private allowedHeaders = new Set<string>(["content-type", "etag", "content-range"]);
  private textTypes = new Set<string>(["application/vnd.apple.mpegurl"]);

  constructor(private http: HttpClient,
              private connectionService: ConnectionService) {
    this.cache = new IndexDBCache(
      this.connectionService,
      "files",
      key => this.loadFileData(key),
    );
  }

  uploadFile(file: File): Observable<TempFile> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<TempFile>(this.apiUrl, formData);
  }

  /**
   * Loads file data from API.
   */
  private loadFileData(url: string): Observable<FileData> {
    return this.http.get(url, {observe: 'response', responseType: 'blob'}).pipe(
      switchMap(async (response) => {
        if (!response.body) {
          throw new Error('Response body is null');
        }

        const headersRecord: Record<string, string> = {};
        response.headers.keys().forEach(key => {
          if (this.allowedHeaders.has(key)) {
            const value = response.headers.get(key);
            if (value !== null) {
              headersRecord[key] = value;
            }
          }
        });

        const contentType = response.headers.get('Content-Type') ?? '';
        let data;
        if (this.textTypes.has(contentType)) {
          data = await response.body.text();
        } else {
          data = await response.body.arrayBuffer();
        }

        return <FileData>{
          url: url,
          data: data,
          headers: headersRecord
        };
      })
    );
  }

  getFileData(url: string): Observable<FileData> {
    return this.cache.get(url).pipe(
      map(value => {
        if (value === undefined) {
          throw new Error(`Unable to load file data: ${url}`);
        }
        return value;
      }));
  }

  isCached(url: string): Observable<boolean> {
    return this.cache.has(url);
  }
}
