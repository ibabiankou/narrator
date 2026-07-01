import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, EMPTY, filter, map, Observable } from 'rxjs';
import { HttpFetcher, Manifest, Publication } from '@readium/shared';
import { environment } from '../../../environments/environment';
import { NavigationItemFragments } from '../models/readium';

@Injectable({
  providedIn: 'root'
})
export class ReadiumService {
  private http = inject(HttpClient);

  private _publication: BehaviorSubject<Publication | undefined> = new BehaviorSubject<Publication | undefined>(undefined);
  publication$ = this._publication.asObservable().pipe(filter(p => p !== undefined));

  private _navigationItemFragments: BehaviorSubject<NavigationItemFragments[] | undefined>
    = new BehaviorSubject<NavigationItemFragments[] | undefined>(undefined);
  navigationItemFragments$ = this._navigationItemFragments.asObservable().pipe(filter(p => p !== undefined));

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

  getUrl(pub: Publication, href: string): string {
    const pathParts = pub.manifest.links.filterByRel("self")[0].href.split('/');
    pathParts.pop();
    return pathParts.join('/') + '/' + href;
  }

  getNavItemFragments(pub: Publication): Observable<NavigationItemFragments[]>{
    if (pub.resources) {
      const mapLinks = pub.resources.items.filter(item => item.href.endsWith("fragment-map.json"));
      if (mapLinks.length > 0) {
        const link = mapLinks[0];
        const fragmentMapUrl = this.getUrl(pub, link.href);
        this.http.get<NavigationItemFragments[]>(fragmentMapUrl)
          .subscribe(fragments => this._navigationItemFragments.next(fragments));
        return this.navigationItemFragments$;
      } else {
        console.error("Publication has no fragment-map.json.");
      }
    } else {
      console.error("Publication has no resources.");
    }
    return EMPTY;
  }
}
