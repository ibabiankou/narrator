import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { map, Observable, switchMap } from 'rxjs';
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

  private cache: IndexDBCache<FileData>;

  private allowedHeaders = new Set<string>(["content-type", "etag", "content-range"]);
  private textTypes = new Set<string>(["application/vnd.apple.mpegurl"]);

  constructor(private http: HttpClient,
              private connectionService: ConnectionService) {
    this.cache = new IndexDBCache(
      this.connectionService,
      "files",
      (key, cachedData) => this.loadFileData(key, cachedData),
    );
  }

  /**
   * Loads file data from API.
   */
  private loadFileData(url: string, cachedData: FileData | undefined): Observable<FileData> {
    let headers = new HttpHeaders();
    if (cachedData && "etag" in cachedData.headers) {
      headers = headers.append("If-None-Match", cachedData.headers["etag"]);
    }

    return this.http.get(url, {headers: headers, observe: 'response', responseType: 'blob'}).pipe(
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

  deleteFromCache(url: string): Observable<void> {
    return this.cache.delete(url);
  }
}
