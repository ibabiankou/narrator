import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { EMPTY, map, Observable, switchMap, throwError } from 'rxjs';
import { HttpFetcher, Manifest, Publication } from '@readium/shared';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ReadiumService {
  private http = inject(HttpClient);

  getPublication(epubKey: string): Observable<Publication> {
    const epubPath = `s3://narrator/${epubKey}`
    const base64EncodedPath = btoa(epubPath).replace(/=+$/, '');
    const manifestUrl = `${environment.readium_base_url}/${base64EncodedPath}/manifest.json`;

    return this.http.get(manifestUrl).pipe(
      map(responseJson => {
        const manifest = Manifest.deserialize(responseJson);
        // TODO: should I fail instead?
        if (!manifest) throw new Error("Publication manifest is undefined.");

        // TODO: Should I use http client instead?
        const fetcher = new HttpFetcher(window.fetch.bind(window), manifestUrl);
        return new Publication({manifest: manifest, fetcher: fetcher});
      }),
    );
  }
}
