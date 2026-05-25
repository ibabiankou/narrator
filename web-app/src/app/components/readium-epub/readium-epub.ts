import { Component, ElementRef, inject, input, OnDestroy, ViewChild } from '@angular/core';
import { EpubNavigator } from '@readium/navigator';
import { Publication } from '@readium/shared';
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
export class ReadiumEpub implements OnDestroy {
  themeService = inject(ThemeService);

  @ViewChild('readerContainer', {static: true}) readerContainer!: ElementRef<HTMLDivElement>;

  publication = input<Publication>();

  private navigator?: EpubNavigator;

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

  ngOnDestroy() {
    if (this.navigator && typeof this.navigator.destroy === 'function') {
      this.navigator.resizeHandler()
      this.navigator.destroy();
    }
  }
}
