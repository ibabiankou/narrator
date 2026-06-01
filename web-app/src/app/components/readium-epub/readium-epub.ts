import { Component, ElementRef, HostListener, inject, input, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { EpubNavigator } from '@readium/navigator';
import { Link, Publication } from '@readium/shared';
import { toObservable } from '@angular/core/rxjs-interop';
import { NOOP_EPUB_LISTENERS } from '../../core/models/readium';
import { ThemeService } from '../../core/services/theme.service';
import { filter, take } from 'rxjs';

@Component({
  selector: 'app-readium-epub',
  imports: [],
  templateUrl: './readium-epub.html',
  styleUrl: './readium-epub.scss',
})
export class ReadiumEpub implements OnInit, OnDestroy {
  themeService = inject(ThemeService);

  @ViewChild('readerContainer', {static: true}) readerContainer!: ElementRef<HTMLDivElement>;

  publication = input<Publication>();

  private navigator?: EpubNavigator;
  private observer!: MutationObserver;

  constructor() {
    toObservable(this.publication)
      .pipe(
        filter(publication => !!publication),
        take(1)
      ).subscribe({
      next: async (publication) => {
        try {
          this.navigator = new EpubNavigator(
            this.readerContainer.nativeElement,
            publication,
            NOOP_EPUB_LISTENERS,
            [],
            undefined,
            {
              preferences: {
                backgroundColor: this.getStyle("background-color"),
                textColor: this.getStyle("color"),
                scroll: true,
                selectionBackgroundColor: "#4e70ff"
              },
              defaults: {
                scroll: true,
                selectionBackgroundColor: "#4e70ff"
              }
            }
          );

          await this.navigator.load();
        } catch (error) {
          console.error('Failed to initialize Readium Navigator:', error);
        }
      }
    });

    this.themeService.isDark$.subscribe({
        next: () => {
          // Wait a bit for css to be updated.
          setTimeout(() => {
            this.syncTheme();
          }, 50);
        }
      }
    );
  }

  ngOnInit() {
    this.startWatchingForIframes();
  }

  private startWatchingForIframes() {
    this.observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node: Node) => {
          if (node instanceof HTMLIFrameElement) {
            this.setupIframeListener(node);
          }
        });
      });
    });

    this.observer.observe(this.readerContainer.nativeElement, {
      childList: true,
      subtree: true
    });
  }

  private setupIframeListener(iframe: HTMLIFrameElement) {
    // Wait for the specific iframe to finish loading its internal DOM
    iframe.addEventListener('load', () => {
      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;

        if (iframeDoc) {
          iframeDoc.addEventListener('keydown', (event: KeyboardEvent) => {
            if (event.key === 'ArrowRight') {
              this.next();
            }
            if (event.key === 'ArrowLeft') {
              this.prev();
            }
          });
        }
      } catch (error) {
        console.error("Failed to attach listener to same-origin iframe:", error);
      }
    });
  }

  private getStyle(variableName: string, target: HTMLElement = document.body): string {
    return getComputedStyle(target).getPropertyValue(variableName).trim();
  }

  private syncTheme() {
    if (!this.navigator) return;
    const editor = this.navigator.preferencesEditor;
    editor.backgroundColor.value = this.getStyle("background-color");
    editor.textColor.value = this.getStyle("color");
    this.navigator.submitPreferences(editor.preferences);
  }

  navigate(link: Link) {
    if (!this.navigator) return;

    this.navigator.go(link.locator, false, () => {});
  }

  @HostListener("document:keydown.arrowright", [])
  next() {
    this.navigator?.goForward(false, () => {
      console.log("Current locator:", this.navigator?.currentLocator.href)
    });
  }

  @HostListener("document:keydown.arrowleft", [])
  prev() {
    this.navigator?.goBackward(false, () => {
      console.log("Current locator:", this.navigator?.currentLocator.href)
    });
  }

  ngOnDestroy() {
    if (this.navigator && typeof this.navigator.destroy === 'function') {
      this.navigator.resizeHandler()
      this.navigator.destroy();
    }
    if (this.observer) {
      this.observer.disconnect();
    }
  }
}
