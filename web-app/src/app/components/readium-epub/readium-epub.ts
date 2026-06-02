import {
  Component,
  ElementRef,
  HostListener,
  inject,
  input,
  OnDestroy,
  OnInit,
  output,
  ViewChild
} from '@angular/core';
import { EpubNavigator } from '@readium/navigator';
import { Link, Publication } from '@readium/shared';
import { toObservable } from '@angular/core/rxjs-interop';
import { NOOP_EPUB_LISTENERS } from '../../core/models/readium';
import { ThemeService } from '../../core/services/theme.service';
import { filter, take } from 'rxjs';
import { TocItem } from '../../core/models/books.dto';

@Component({
  selector: 'app-readium-epub',
  imports: [],
  templateUrl: './readium-epub.html',
  styleUrl: './readium-epub.scss',
})
export class ReadiumEpub implements OnInit, OnDestroy {
  themeService = inject(ThemeService);

  @ViewChild('readerContainer', {static: true}) readerContainer!: ElementRef<HTMLDivElement>;

  publication = input.required<Publication>();
  toc = input.required<TocItem[]>();
  private currentItem = 0;
  currentItemChanged = output<number>();
  toggleItem = output<number>();

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
                selectionBackgroundColor: "#4e70ff",
                scrollPaddingTop: 24,
                scrollPaddingBottom: 24
              },
              defaults: {
                scroll: true,
                selectionBackgroundColor: "#4e70ff",
                scrollPaddingTop: 24,
                scrollPaddingBottom: 24
              }
            }
          );

          await this.navigator.load().then(() => {
            this.navigate(0);
          });
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
            if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
              this.next();
            }
            if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
              this.prev();
            }
            if (event.key === 'Space') {
              this.toggle();
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

  navigate(tocIndex: number) {
    if (!this.navigator) return;
    if (this.currentItem === tocIndex) return;
    if (tocIndex < 0 || tocIndex >= this.toc().length) return;

    const link = new Link({href: this.toc()[tocIndex].href});
    this.navigator.go(link.locator, false, (ok) => {
      if (ok) {
        this.currentItem = tocIndex;
        this.currentItemChanged.emit(tocIndex);
        console.log("Successfully navigated to", this.navigator!.currentLocator.href);
      } else {
        console.log("Navigation is not successful.")
      }
    });
  }

  @HostListener("document:keydown.arrowright", [])
  @HostListener("document:keydown.arrowdown", [])
  next() {
    this.navigate(this.currentItem + 1);
  }

  @HostListener("document:keydown.arrowleft", [])
  @HostListener("document:keydown.arrowup", [])
  prev() {
    this.navigate(this.currentItem - 1);
  }

  @HostListener("document:keydown.space", [])
  toggle() {
    this.toggleItem.emit(this.currentItem);
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
