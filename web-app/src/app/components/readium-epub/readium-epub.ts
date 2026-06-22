import {
  Component, computed,
  effect,
  ElementRef,
  HostListener,
  inject,
  input,
  NgZone,
  OnDestroy,
  OnInit,
  output,
  ViewChild
} from '@angular/core';
import { EpubNavigator, TextAlignment } from '@readium/navigator';
import { Link, Publication } from '@readium/shared';
import { NOOP_EPUB_LISTENERS } from '../../core/models/readium';
import { ThemeService } from '../../core/services/theme.service';
import { TocItem } from '../../core/models/books.dto';
import { environment } from '../../../environments/environment';
import { SettingsService } from '../../core/services/settings.service';
import { toSignal } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-readium-epub',
  imports: [],
  templateUrl: './readium-epub.html',
  styleUrl: './readium-epub.scss',
})
export class ReadiumEpub implements OnInit, OnDestroy {
  private settingsService = inject(SettingsService);
  private themeService = inject(ThemeService);
  private ngZone = inject(NgZone);

  @ViewChild('readerContainer', {static: true}) readerContainer!: ElementRef<HTMLDivElement>;

  publication = input.required<Publication>();
  toc = input.required<TocItem[]>();
  private currentItem = 0;
  currentItemChanged = output<number>();

  private navigator?: EpubNavigator;
  private observer!: MutationObserver;
  private fragmentMap = new Map<string, string>();
  private currentFragment?: string;

  private preferences = toSignal(this.settingsService.userPreferences$);
  private readAlong = computed(() => !!this.preferences()!["auto_scroll"]);

  constructor() {
    effect(() => {
      this.initNavigator();
    });
    effect(() => {
      const currentReadAlong = this.readAlong();
      if (currentReadAlong) {
        if (this.currentFragment) {
          this.showFragment(this.currentFragment);
        }
      } else {
        this.removeHighlight();
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

  async initNavigator() {
    const publication = this.publication();
    if (!publication) {
      console.log("No publication to initialize navigator.");
      return;
    }
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
            scrollPaddingBottom: 24,
            scrollPaddingLeft: 8,
            scrollPaddingRight: 8,
            textAlign: TextAlignment.justify,
            fontSize: 1.75
          },
          defaults: {
            scroll: true,
            selectionBackgroundColor: "#4e70ff",
          },
          injectables: {
            rules: [
              {
                resources: [/.*\.x?html?/],
                append: [
                  {
                    as: "link",
                    rel: "stylesheet",
                    target: "head",
                    url: `${document.location.origin}/app/css/epub-read-along.css`,
                    type: "text/css"
                  }
                ]
              }
            ],
            allowedDomains: [environment.origin]
          }
        }
      );

      await this.navigator.load().then(() => {
        if (this.currentFragment) {
          this.showFragment(this.currentFragment);
        } else {
          this.navigate(0);
        }
      });
    } catch (error) {
      console.error('Failed to initialize Readium Navigator:', error);
    }

    try {
      if (publication.resources) {
        const mapLinks = publication.resources.items.filter(item => item.href.endsWith("fragment-map.json"));
        if (mapLinks.length > 0) {
          const link = mapLinks[0];
          const mapData: object = <Object>await publication.get(link).readAsJSON();
          Object.entries(mapData).forEach(([href, values]) => {
            if (Array.isArray(values)) {
              values.forEach((fragmentId: string) => {
                this.fragmentMap.set(fragmentId, href);
              });
            }
          });
        } else {
          console.error("No fragment map found in publication.");
        }
      }
    } catch (error) {
      console.error('Failed to load fragment map.', error);
    }
  }

  @HostListener('document:visibilitychange')
  async handleVisibilityChange() {
    if (document.visibilityState !== 'visible') {
      if (this.navigator) {
        await this.navigator.destroy();
      }
    } else {
      await this.initNavigator();
    }
  }

  ngOnInit() {
    this.startWatchingForIframes();
  }

  private startWatchingForIframes() {
    this.ngZone.runOutsideAngular(() => {
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
    });
  }

  private setupIframeListener(iframe: HTMLIFrameElement) {
    // Wait for the specific iframe to finish loading its internal DOM
    iframe.addEventListener('load', () => {
      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
        if (iframeDoc) {
          // Forward events to the parent window to support keyboard shortcuts and hide-idle directive.
          const eventsToForward = ['mousemove', 'keydown', 'touchstart'];
          eventsToForward.forEach(eventName => {
            iframeDoc.addEventListener(eventName, (e) => {
              this.ngZone.run(() => {
                let clonedEvent: Event;

                try {
                  // Use the specific constructor to map all original properties automatically
                  if (eventName == "mousemove") {
                    clonedEvent = new MouseEvent(eventName, e);
                  } else if (eventName == "keydown") {
                    e.preventDefault();
                    e.stopPropagation();
                    clonedEvent = new KeyboardEvent(eventName, e);
                  } else if (eventName == "touchstart" && e instanceof TouchEvent) {
                    clonedEvent = new TouchEvent(eventName, {
                      bubbles: e.bubbles,
                      cancelable: e.cancelable,
                      composed: e.composed,
                      detail: e.detail,
                      view: e.view,
                      touches: Array.from(e.touches),
                      targetTouches: Array.from(e.targetTouches),
                      changedTouches: Array.from(e.changedTouches),
                      ctrlKey: e.ctrlKey,
                      metaKey: e.metaKey,
                      shiftKey: e.shiftKey,
                      altKey: e.altKey
                    });
                  } else {
                    clonedEvent = new Event(eventName, e);
                  }
                } catch (err) {
                  console.error(`Failed to clone event '${eventName}' for forwarding:`, err);
                  // Fallback for older browsers or strict constructor edge cases
                  clonedEvent = new Event(eventName, e);
                }
                window.dispatchEvent(clonedEvent);
              });
            }, { passive: false });
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
        this.updateCurrentItem(tocIndex);
        console.log("Successfully navigated to", this.navigator!.currentLocator.href);
      } else {
        console.log("Navigation is not successful.")
      }
    });
  }

  private updateCurrentItem(index: number) {
    if (this.currentItem === index) return;
    this.currentItem = index;
    this.currentItemChanged.emit(index);
  }

  navigateHref(href: string, cb: (ok: boolean) => void) {
    if (!this.navigator) return;

    const link = new Link({href: href});
    this.navigator.go(link.locator, false, (ok: boolean) => {
      if (ok) {
        const tocIndex = this.toc().findIndex(i => {return i.href === href})
        if (tocIndex >= 0) {
          this.updateCurrentItem(tocIndex);
        }
      }
      cb(ok);
    });
  }

  showFragment(fragmentId: string) {
    console.log("showFragment", fragmentId);
    this.currentFragment = fragmentId;

    if (!this.readAlong()) {
      return;
    }

    if (!this.navigator) return;
    const pageHref = this.fragmentMap.get(fragmentId);
    if (!pageHref) {
      console.warn("Fragment", fragmentId, "not found in map of size", this.fragmentMap.size);
      return;
    }
    if (pageHref == this.navigator.currentLocator.href) {
      // No need to navigate.
      this.doShowFrag(fragmentId);
    } else {
      // Navigate and show
      this.navigateHref(pageHref, (_) => {
        this.doShowFrag(fragmentId);
      });
    }
  }

  private doShowFrag(fragmentId: string) {
    if (!this.navigator) return;
    // This kind of access into the guts of epub renderer feels fragile.
    const frames = this.navigator.pool.currentFrames.filter(f => !!f);
    if (frames) {
      const doc = frames[0].window.document;
      const el = doc.getElementById(fragmentId);
      if (!el) {
        console.error("Failed to getElementById for fragment", fragmentId);
        return;
      }
      this.updateStyles(doc, el);
    }
  }

  private currentElement: Element | null = null;

  private updateStyles(doc: Document, targetElement: HTMLElement) {
    // Find all elements in the exact order they appear on the page.
    const elements = doc.querySelectorAll("span.nf");

    // Make target element the current one.
    if (this.currentElement) {
      this.currentElement.classList.remove("current");
    }
    targetElement.classList.add("current");
    this.currentElement = targetElement;

    targetElement.scrollIntoView({behavior: "smooth", block: "center", inline: "nearest"});

    // Ensure all past and future elements marked as such.
    let foundTarget = false;
    for (let i = 0; i < elements.length; i++) {
      const el = elements[i];

      if (el.id === targetElement.id) {
        foundTarget = true;
        continue;
      }

      if (!foundTarget) {
        if (!el.classList.contains("past")) {
          el.classList.add("past");
        }
      } else {
        if (el.classList.contains("past")) {
          el.classList.remove("past")
        }
      }
    }
  }

  private removeHighlight() {
    if (!this.navigator) return;
    // This kind of access into the guts of epub renderer feels fragile.
    const frames = this.navigator.pool.currentFrames.filter(f => !!f);
    if (frames) {
      const doc = frames[0].window.document;

      const elements = doc.querySelectorAll("span.nf");
      for (const el of elements) {
        el.classList.remove("past", "current")
      }
      this.currentElement = null;
    }
  }

  ngOnDestroy() {
    if (this.navigator && typeof this.navigator.destroy === 'function') {
      this.navigator.destroy();
    }
    if (this.observer) {
      this.observer.disconnect();
    }
  }
}
