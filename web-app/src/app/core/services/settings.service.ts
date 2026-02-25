import { Injectable } from '@angular/core';
import { Settings } from '../models/books.dto';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { BehaviorSubject, filter, switchMap, tap } from 'rxjs';
import { IndexDBCache } from './indexDBCache';
import { ConnectionService } from './connection.service';
import { mergeDeep } from '../utils';

@Injectable({providedIn: 'root'})
export class SettingsService {

  private apiUrl = `${environment.api_base_url}/settings`;
  private settingsCache: IndexDBCache<Settings>;

  private _userPreferences$ = new BehaviorSubject<Settings | undefined>(undefined);
  readonly userPreferences$ = this._userPreferences$.asObservable().pipe(filter(value => value !== undefined));

  constructor(private http: HttpClient, private connectionService: ConnectionService) {
    this.settingsCache = new IndexDBCache(
      this.connectionService,
      "settings",
      (url: string) => {
        return this.http.get<Settings>(url);
      },
      (url: string, payload: Settings) => {
        return this.http.patch<Settings>(url, payload);
      });

    this.get('user_preferences').subscribe(preferences => this._userPreferences$.next(preferences));
  }

  get(kind: string) {
    const url = `${this.apiUrl}/${kind}`;
    return this.settingsCache.get(url)
      .pipe(tap(patched => {
        if (url.endsWith('user_preferences')) {
          this._userPreferences$.next(patched)
        }
      }));
  }

  patch(kind: string, payload: Partial<Settings>) {
    const url = `${this.apiUrl}/${kind}`;

    let setOperation;
    if (!this.connectionService.isOnline()) {
      // Handling offline mode explicitly so that multiple consequent patch operations are merged into one
      // instead of overriding each other.
      setOperation = this.get(kind).pipe(
        switchMap(settings => this.settingsCache.set(url, mergeDeep(settings, payload)))
      )
    } else {
      setOperation = this.settingsCache.set(url, payload);
    }

    return setOperation.pipe(
      switchMap(() => this.get(kind)),
      tap(patched => {
        if (url.endsWith('user_preferences')) {
          this._userPreferences$.next(patched)
        }
      })
    );
  }
}
