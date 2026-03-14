import { Component, Injector, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatIconModule, MatIconRegistry } from '@angular/material/icon';
import { fromPromise } from 'rxjs/internal/observable/innerFrom';
import { SettingsService } from './core/services/settings.service';
import { ThemeService } from './core/services/theme.service';
import { of, retry, switchMap, take, throwError, timer } from 'rxjs';
import { VERSION } from '../environments/version';
import { AuthService } from './core/services/authService';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, MatIconModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  constructor(iconRegistry: MatIconRegistry,
              injector: Injector,
              settingsService: SettingsService,
              themeService: ThemeService,
              authHeartbeat: AuthService) {
    iconRegistry.setDefaultFontSetClass('material-symbols-outlined');
    ServiceLocator.injector = injector;

    fromPromise(this.requestPersistentStorage()).subscribe();

    settingsService.userPreferences$.pipe(
      switchMap(preferences => {
          if (preferences['theme'] !== undefined) {
            return of(preferences['theme']);
          } else {
            return throwError(() => new Error("User preferences are not available!"));
          }
        }
      ),
      retry({
        count: 5,
        delay: (count) => timer(2 ^ count * 50 * (0.75 + 0.5 * Math.random()))
      }),
      take(1)
    ).subscribe(theme => {
      themeService.setTheme(theme);
    })
  }

  ngOnInit(): void {
    console.log(
      `%c Version: ${VERSION.commit} | Built on: ${VERSION.buildDate} `,
      'background: #222; color: #bada55; padding: 2px 5px; border-radius: 3px;'
    );
  }

  async requestPersistentStorage() {
    if (navigator.storage && navigator.storage.persist) {
      const isPersisted = await navigator.storage.persist();
      if (isPersisted) {
        console.log("Storage will not be cleared except by explicit user action.");
      } else {
        console.warn("Storage is still 'Best Effort' and may be evicted.");
      }
    }
  }
}

export class ServiceLocator {
  static injector: Injector;
}
