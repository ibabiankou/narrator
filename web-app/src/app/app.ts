import { Component, Injector } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatIconModule, MatIconRegistry } from '@angular/material/icon';
import { fromPromise } from 'rxjs/internal/observable/innerFrom';
import { SettingsService } from './core/services/settings.service';
import { ThemeService } from './core/services/theme.service';
import { of, retry, switchMap, take, throwError, timer } from 'rxjs';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, MatIconModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  constructor(iconRegistry: MatIconRegistry,
              injector: Injector,
              settingsService: SettingsService,
              themeService: ThemeService) {
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
