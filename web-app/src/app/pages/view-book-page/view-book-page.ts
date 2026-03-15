import {
  AfterViewInit,
  Component,
  computed, effect,
  ElementRef,
  inject,
  input,
  model,
  QueryList,
  Signal,
  signal,
  TemplateRef,
  viewChild,
  ViewChildren,
  WritableSignal
} from '@angular/core';
import { BookPage, BookStatus, BookWithContent, DownloadInfo } from '../../core/models/books.dto';
import { BooksService } from '../../core/services/books.service';
import { BehaviorSubject, filter, interval, Observable, repeat, Subscription, switchMap, take, tap, timer } from 'rxjs';
import { MatIcon } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { SectionComponent } from '../../components/section/section.component';
import { PlayerComponent } from '../../components/player/player.component';
import { Title } from '@angular/platform-browser';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import { MatButton, MatIconButton } from '@angular/material/button';
import {
  MatDialog,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogTitle
} from '@angular/material/dialog';
import {
  ActionButtonContentDirective,
  BreadcrumbContentDirective,
  ToolbarComponent
} from '../../components/toolbar/toolbar.component';
import { DownloadService } from '../../core/services/download.service';
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';
import { MatButtonToggle, MatButtonToggleGroup } from '@angular/material/button-toggle';
import { ThemeService } from '../../core/services/theme.service';
import { SettingsService } from '../../core/services/settings.service';
import { HideIdleDirective } from '../../core/hideIdleDirective';
import { PdfPage } from '../../components/pdf-page/pdf-page';
import { VisibilityDirective } from '../../core/visibilityDirective';
import { binarySearch } from '../../core/utils';
import { OwnerDirective } from '../../core/ownerDirective';

@Component({
  selector: 'app-view-book-page',
  imports: [
    MatIcon,
    SectionComponent,
    PlayerComponent,
    SkeletonComponent,
    MatIconButton,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatButton,
    MatDialogClose,
    ToolbarComponent,
    BreadcrumbContentDirective,
    ActionButtonContentDirective,
    MatMenuTrigger,
    MatMenu,
    MatMenuItem,
    MatButtonToggleGroup,
    MatButtonToggle,
    HideIdleDirective,
    PdfPage,
    VisibilityDirective,
    RouterLink,
    OwnerDirective,
  ],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage implements AfterViewInit {
  private booksService = inject(BooksService);
  private downloadService = inject(DownloadService);
  private titleService = inject(Title);
  private dialog = inject(MatDialog);
  private settingsService: SettingsService = inject(SettingsService);
  private themeService: ThemeService = inject(ThemeService);

  bookId = input.required<string>();

  private $bookWithContent: Observable<BookWithContent>;
  bookWithContent: Signal<BookWithContent>;
  pages: Signal<BookPage[]>;
  pagesWindow = model<BookPage[]>([]);

  downloadInfo: WritableSignal<DownloadInfo | undefined> = signal(undefined);
  isDownloaded = computed(() => this.downloadInfo() != undefined);
  isDownloading = computed(() => {
    const info = this.downloadInfo();
    if (!info) {
      return false;
    }
    return !(info.fragments_total > 0 && info.fragments_downloaded == info.fragments_total);
  });

  settings = toSignal(this.settingsService.userPreferences$);

  private downloadSubscription: Subscription | null = null;

  isShowingPages = computed(() => this.settings()!["viewer_mode"] === "both");

  protected currentSectionId = 0;
  private $currentSectionId = new BehaviorSubject(0);

  readonly storageInfoTemplate = viewChild.required('storageInfoTemplate', {read: TemplateRef});
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
            filter((book) => book.overview.status == BookStatus.ready),
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

    // Continue download if it's not completed.
    this.downloadSubscription = toObservable(this.downloadInfo)
      .pipe(
        take(1),
        filter(info => !!info),
        filter(info => info && (info.fragments_total == 0 || info.fragments_total > info.fragments_downloaded)),
        switchMap(() => this.downloadService.downloadBook(this.bookId())),
      )
      .subscribe({
        complete: () => {
          this.downloadSubscription = null;
          this.reloadDownloadInfo();
        }
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

  protected downloadBookDialog(templateRef: TemplateRef<any>) {
    const dialogRef = this.dialog.open(templateRef);

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.downloadSubscription = this.downloadService.downloadBook(this.bookId()).subscribe();
        this.reloadDownloadInfo();
        this.storageInfoDialog(this.storageInfoTemplate());
      }
    });
  }

  protected storageInfoDialog(templateRef: TemplateRef<any>) {
    const dialogRef = this.dialog.open(templateRef);

    const reloadInterval = interval(500).subscribe(() => this.reloadDownloadInfo());
    dialogRef.afterClosed().subscribe(result => {
      reloadInterval.unsubscribe();
      if (result) {
        if (this.downloadSubscription) {
          this.downloadSubscription.unsubscribe();
          this.downloadSubscription = null;
        }
        this.downloadService.deleteBookData(this.bookId());
        this.reloadDownloadInfo();
      }
    });
  }

  private formatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  });

  protected totalSizeMb() {
    return this.formatter.format(this.bookWithContent().stats.total_size_bytes / 1024 / 1024);
  }

  protected downloadProgressPercent(): string {
    const info = this.downloadInfo();
    if (!info || info.fragments_total == 0) {
      return "0";
    } else {
      return this.formatter.format(info.fragments_downloaded / info.fragments_total * 100);
    }
  }

  private reloadDownloadInfo() {
    this.downloadService.getDownloadInfo(this.bookId())
      .subscribe(val => this.downloadInfo.set(val));
  }

  protected setTheme(theme: string) {
    this.themeService.setTheme(theme);
    this.settingsService.patch("user_preferences", {theme: theme}).subscribe();
  }
}
