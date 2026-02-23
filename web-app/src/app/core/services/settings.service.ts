import { Injectable } from '@angular/core';
import { Settings } from '../models/books.dto';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { BehaviorSubject, filter, tap } from 'rxjs';

@Injectable({providedIn: 'root'})
export class SettingsService {

  private apiUrl = `${environment.api_base_url}/settings`;

  private _userPreferences$ = new BehaviorSubject<Settings | undefined>(undefined);
  readonly userPreferences$ = this._userPreferences$.asObservable().pipe(filter(value => value !== undefined));

  constructor(private http: HttpClient) {
    this.get('user_preferences').subscribe(preferences => this._userPreferences$.next(preferences));
  }

  get(kind: string) {
    return this.http.get<Settings>(`${this.apiUrl}/${kind}`)
      .pipe(tap(patched => {
        if (kind === 'user_preferences') {
          this._userPreferences$.next(patched)
        }
      }));
  }

  patch(kind: string, payload: Partial<Settings>) {
    return this.http.patch<Settings>(`${this.apiUrl}/${kind}`, payload)
      .pipe(tap(patched => {
        if (kind === 'user_preferences') {
          this._userPreferences$.next(patched)
        }
      }));
  }
}
