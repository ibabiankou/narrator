import { Component, ElementRef, HostListener, inject, input, OnDestroy, ViewChild } from '@angular/core';
import { BreadcrumbContentDirective, ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { EpubNavigator, EpubNavigatorListeners, KeyboardPeripheralEventData } from '@readium/navigator';
import { HttpFetcher, Locator, Manifest, Publication } from '@readium/shared';
import { toObservable } from '@angular/core/rxjs-interop';
import { filter, map, switchMap } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import {
  BasicTextSelection,
  ContextMenuEvent,
  FrameClickEvent,
  SuspiciousActivityEvent
} from '@readium/navigator-html-injectables';
import { ThemeService } from '../../core/services/theme.service';

// noinspection JSUnusedLocalSymbols
const listeners: EpubNavigatorListeners = {
  frameLoaded: (wnd: Window) => {
  },
  positionChanged: (locator: Locator) => {
  },
  tap: (e: FrameClickEvent) => {
    return true
  },
  click: (e: FrameClickEvent) => {
    return true
  },
  zoom: (scale: number) => {
  },
  miscPointer: (amount: number) => {
  },
  scroll: (delta: number) => {
  },
  customEvent: (key: string, data: unknown) => {
  },
  handleLocator: (locator: Locator) => {
    return true
  },
  textSelected: (selection: BasicTextSelection) => {
  },
  contentProtection: (type: string, data: SuspiciousActivityEvent) => {
  },
  contextMenu: (data: ContextMenuEvent) => {
  },
  peripheral: (data: KeyboardPeripheralEventData) => {
  }
}

@Component({
  selector: 'app-view-readium',
  imports: [
    ToolbarComponent,
    BreadcrumbContentDirective,
  ],
  templateUrl: './view-readium.html',
  styleUrl: './view-readium.scss',
})
export class ViewReadium implements OnDestroy {
  httpClient = inject(HttpClient);
  themeService = inject(ThemeService);

  file = input.required<string>();

  @ViewChild('readerContainer', {static: true}) readerContainer!: ElementRef<HTMLDivElement>;

  private navigator?: EpubNavigator;
  private baseUrl?: string;

  constructor() {
    toObservable(this.file).pipe(
      filter(fileParam => !!fileParam),
      switchMap((filePath) => {
        const base64EncodedPath = btoa(filePath).replace(/=+$/, '');
        this.baseUrl = `http://localhost:15080/webpub/${base64EncodedPath}/`;
        const manifestUrl = `${this.baseUrl}manifest.json`;
        return this.httpClient.get(manifestUrl);
      }),
      map(responseJson => {
        return Manifest.deserialize(responseJson)
      }),
      filter(value => value != undefined)
    ).subscribe({
      next: async (manifest) => {
        try {
          const fetcher = new HttpFetcher(window.fetch.bind(window), this.baseUrl);
          const publication = new Publication({manifest: manifest, fetcher: fetcher});
          this.navigator = new EpubNavigator(
            this.readerContainer.nativeElement,
            publication,
            listeners,
            [],
            undefined,
            {
              preferences: {
                backgroundColor: this.getStyle("background-color"),
                textColor: this.getStyle("color"),
                scroll: true
              },
              defaults: {}
            }
          );

          await this.navigator.load();
        } catch (error) {
          console.error('Failed to initialize Readium Navigator:', error);
        }
      }
    });

    this.themeService.isDark$.subscribe(
      {
        next: () => {
          // Wait a bit for css to be updated.
          setTimeout(() => {
            this.updatePreferences();
          }, 50);
        }
      }
    );
  }

  private getStyle(variableName: string, target: HTMLElement = document.body): string {
    return getComputedStyle(target).getPropertyValue(variableName).trim();
  }

  private updatePreferences() {
    if (!this.navigator) return;

    const editor = this.navigator.preferencesEditor;

    editor.backgroundColor.value = this.getStyle("background-color");
    editor.textColor.value = this.getStyle("color");

    this.navigator.submitPreferences(editor.preferences);
  }

  @HostListener("document:keydown.arrowright", [])
  next() {
    this.navigator?.goForward(false, () => {
    });
  }

  @HostListener("document:keydown.arrowleft", [])
  prev() {
    this.navigator?.goBackward(false, () => {
    });
  }

  ngOnDestroy(): void {
    if (this.navigator && typeof this.navigator.destroy === 'function') {
      this.navigator.destroy();
    }
  }
}
