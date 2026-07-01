import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, filter, map, Observable } from 'rxjs';
import { HttpFetcher, Manifest, Publication } from '@readium/shared';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ReadiumService {
  private http = inject(HttpClient);

  private _publication: BehaviorSubject<Publication | undefined> = new BehaviorSubject<Publication | undefined>(undefined);
  publication$ = this._publication.asObservable().pipe(filter(p => p !== undefined));

  getPublication(epubKey: string): Observable<Publication> {
    const epubPath = `s3://narrator/${epubKey}`
    const base64EncodedPath = btoa(epubPath).replace(/=+$/, '');
    const manifestUrl = `${environment.readium_base_url}/${base64EncodedPath}/manifest.json`;

    this.http.get(manifestUrl).pipe(
      map(responseJson => {
        const manifest = Manifest.deserialize(responseJson);
        // TODO: should I fail instead?
        if (!manifest) throw new Error("Publication manifest is undefined.");

        // TODO: Should I use http client instead?
        const fetcher = new HttpFetcher(window.fetch.bind(window), manifestUrl);
        return new Publication({manifest: manifest, fetcher: fetcher});
      }),
    ).subscribe(publication => this._publication.next(publication));

    return this.publication$;
  }
}
