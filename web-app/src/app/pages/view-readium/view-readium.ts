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

// noinspection JSUnusedLocalSymbols
const listeners: EpubNavigatorListeners = {
  frameLoaded: (wnd: Window) => {
    console.log('frameLoaded:', wnd);
  },
  positionChanged: (locator: Locator) => {
    console.log('Position changed:', locator);
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
    console.log('text selected:', selection);
  },
  contentProtection: (type: string, data: SuspiciousActivityEvent) => {
  },
  contextMenu: (data: ContextMenuEvent) => {
    console.log('contextMenu:', data);
  },
  peripheral: (data: KeyboardPeripheralEventData) => {
    console.log('peripheral:', data);
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

  file = input.required<string>();

  @ViewChild('readerContainer', {static: true}) readerContainer!: ElementRef<HTMLDivElement>;

  private navigator?: EpubNavigator;
  private baseUrl?: string;

  constructor() {
    toObservable(this.file).pipe(
      filter(fileParam => !!fileParam),
      switchMap((filePath) => {
        const base64EncodedPath = btoa(filePath);
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
          this.navigator = new EpubNavigator(
            this.readerContainer.nativeElement,
            new Publication({manifest: manifest, fetcher: fetcher}),
            listeners,
            [],
            undefined,
            {
              preferences: {
                backgroundColor: "#666",
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
  }

  @HostListener("document:keydown.arrowright", [])
  next() {
    console.log("right");
    this.navigator?.goForward(false, (ok) => {
      console.log("goForward callback", ok);
    });
  }

  @HostListener("document:keydown.arrowleft", [])
  prev() {
    console.log("left");
    this.navigator?.goBackward(false, (ok) => {
      console.log("goBackward callback", ok);
    });
  }

  ngOnDestroy(): void {
    if (this.navigator && typeof this.navigator.destroy === 'function') {
      this.navigator.destroy();
    }
  }
}
