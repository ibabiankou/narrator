import {
  AfterViewInit,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  input,
  model,
  OnInit,
  QueryList,
  Signal,
  ViewChildren
} from '@angular/core';
import { BookPage, BookStatus, BookWithContent } from '../../core/models/books.dto';
import { BooksService } from '../../core/services/books.service';
import { BehaviorSubject, filter, Observable, repeat, switchMap, take, tap, timer } from 'rxjs';
import { SectionComponent } from '../../components/section/section.component';
import { PlayerComponent } from '../../components/player/player.component';
import { Title } from '@angular/platform-browser';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import {
  ActionButtonContentDirective,
  BreadcrumbContentDirective,
  ToolbarComponent
} from '../../components/toolbar/toolbar.component';
import { HideIdleDirective } from '../../core/hideIdleDirective';
import { binarySearch } from '../../core/utils';
import { BookMenu } from '../../components/book-menu/book-menu/book-menu';
import { RouterLink } from '@angular/router';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { MatTooltip } from '@angular/material/tooltip';
import { SettingsService } from '../../core/services/settings.service';

@Component({
  selector: 'app-view-book-page',
  imports: [
    SectionComponent,
    PlayerComponent,
    SkeletonComponent,
    ToolbarComponent,
    BreadcrumbContentDirective,
    ActionButtonContentDirective,
    HideIdleDirective,
    BookMenu,
    RouterLink,
    MatIcon,
    MatIconButton,
    MatTooltip,
  ],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage implements OnInit, AfterViewInit {
  private booksService = inject(BooksService);
  private titleService = inject(Title);
  private settingsService = inject(SettingsService);

  bookId = input.required<string>();

  private $bookWithContent: Observable<BookWithContent>;
  bookWithContent: Signal<BookWithContent>;
  pages: Signal<BookPage[]>;
  pagesWindow = model<BookPage[]>([]);

  protected currentSectionId = 0;
  private $currentSectionId = new BehaviorSubject(0);

  @ViewChildren("section", {"read": ElementRef}) sectionElements!: QueryList<ElementRef>;

  constructor() {
    this.$bookWithContent = toObservable(this.bookId).pipe(
      switchMap(id =>
        this.booksService.getBookWithContent(id)
          .pipe(
            repeat({
              count: 25,
              delay: (count) => timer(2 ^ count * 300 * (0.75 + 0.5 * Math.random()))
            }),
            filter((book) => BookStatus.ge(book.overview.status, BookStatus.queued)),
            take(1),
            tap(book => this.titleService.setTitle(`${book.overview.title} - NNarrator`)),
          )
      )
    );
    const bookWithContentSignal = toSignal(this.$bookWithContent);
    this.bookWithContent = computed(() => bookWithContentSignal()!);
    this.pages = computed(() => this.bookWithContent()?.pages);

    effect(() => {
      const pages = this.pages();
      if (pages == undefined || pages.length == 0) {
        return;
      }

      this.$currentSectionId
        .subscribe((sectionId => {
            let pagesWindow;
            if (sectionId == 0) {
              pagesWindow = pages.slice(0, 10);
            } else {
              const sections = pages.flatMap(p => p.sections);
              const sectionIndex = binarySearch(sections, s => s.id, sectionId);
              const currentPageIndex = sections[sectionIndex].page_index; // cannot read property of undefined

              // find start index
              let contextBefore = 2; // number of pages with content before and after the current section;
              let startIndex = 0;
              for (let i = currentPageIndex-1; i >= 0; i--) {
                if (pages[i].sections.length > 0) {
                  contextBefore--;
                } else {
                  continue;
                }
                if (contextBefore == 0) {
                  startIndex = i;
                  break;
                }
              }

              // find end index
              let contextAfter = 2; // number of pages with content before and after the current section;
              let endIndex = pages.length - 1;
              for (let i = currentPageIndex+1; i < pages.length; i++) {
                if (pages[i].sections.length > 0) {
                  contextAfter--;
                } else {
                  continue;
                }
                if (contextAfter == 0) {
                  endIndex = i;
                  break;
                }
              }

              const startPageIndex = Math.max(0, startIndex);
              const endPageIndex = Math.min(pages.length, endIndex + 1); // adjust for exclusive end index
              pagesWindow = pages.slice(startPageIndex, endPageIndex);
            }
            this.pagesWindow.set(pagesWindow);
          })
        );
    });
  }

  ngOnInit() {
    this.settingsService.userPreferences$
      .pipe(take(1))
      .subscribe(preferences => {
        this.settingsService.setFontSizeStyle(preferences["text_size"]);
      });
  }

  ngAfterViewInit() {
    this.scrollToSection(this.currentSectionId);
    this.sectionElements.changes.subscribe(() => {
      // TODO: There is race condition between this handler and updating pagesWindow.
      //  So, sometimes it scrolls in the wrong direction.
      this.scrollToSection(this.currentSectionId);
    })
  }

  scrollToSection(sectionId: number) {
    if (sectionId == 0) return;
    const selector = `section-${sectionId}`;
    const element = this.sectionElements.find(e => e.nativeElement.id == selector);
    if (element) {
      element.nativeElement.scrollIntoView({behavior: "smooth", block: "center"});
    } else {
      console.warn("Section that is being played is not found. Section id:", sectionId);
    }
  }

  protected setCurrentSectionId(sectionId: number) {
    this.currentSectionId = sectionId;
    this.$currentSectionId.next(sectionId);
    this.scrollToSection(sectionId);
  }

  protected copyBookTitle() {
    navigator.clipboard.writeText(this.bookWithContent()?.overview.title ?? "");
  }

  protected readonly BookStatus = BookStatus;
}
