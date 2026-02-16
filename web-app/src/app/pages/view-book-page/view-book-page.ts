import {
  AfterViewInit,
  Component,
  computed,
  ElementRef,
  inject,
  input,
  model,
  QueryList, signal,
  TemplateRef,
  viewChild,
  ViewChildren, WritableSignal
} from '@angular/core';
import { BookStatus, DownloadInfo, Section } from '../../core/models/books.dto';
import { BooksService } from '../../core/services/books.service';
import { BehaviorSubject, filter, interval, repeat, Subscription, switchMap, take, tap, timer } from 'rxjs';
import { MatIcon } from '@angular/material/icon';
import { Router } from '@angular/router';
import { SectionComponent } from '../../components/section/section.component';
import { PlayerComponent } from '../../components/player/player.component';
import { AsyncPipe } from '@angular/common';
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

@Component({
  selector: 'app-view-book-page',
  imports: [
    MatIcon,
    SectionComponent,
    PlayerComponent,
    AsyncPipe,
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
  ],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage implements AfterViewInit {
  private booksService = inject(BooksService);
  private downloadService = inject(DownloadService);
  private titleService = inject(Title);
  private dialog = inject(MatDialog);
  private router: Router = inject(Router);
  private themeService: ThemeService = inject(ThemeService);

  bookId = input.required<string>();

  private _bookWithContent = toSignal(
    toObservable(this.bookId).pipe(
      switchMap(id =>
        this.booksService.getBookWithContent(id)
          .pipe(
            repeat({
              count: 25,
              delay: (count) => timer(2 ^ count * 300 * (0.75 + 0.5 * Math.random()))
            }),
            filter((book) => book.overview.status == BookStatus.ready),
            take(1),
          )
      ),
      tap(book => this.titleService.setTitle(`${book.overview.title} - NNarrator`)),
    ));
  bookWithContent = computed(() => this._bookWithContent()!);
  pages = computed(() => this.bookWithContent().pages);

  downloadInfo: WritableSignal<DownloadInfo | undefined> = signal(undefined);
  isDownloaded = computed(() => this.downloadInfo() != undefined);
  isDownloading = computed(() => {
    const info = this.downloadInfo();
    if (!info) {
      return false;
    }
    return !(info.fragments_total > 0 && info.fragments_downloaded == info.fragments_total);
  });

  private downloadSubscription: Subscription | null = null;

  isEditingSection = model(false);
  isShowingPages = model(false);

  $currentSectionId = new BehaviorSubject<number>(0);

  readonly storageInfoTemplate = viewChild.required('storageInfoTemplate', {read: TemplateRef});
  @ViewChildren("section", {"read": ElementRef}) sectionElements!: QueryList<ElementRef>;

  constructor() {
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
    this.scrollToSection(this.$currentSectionId.value);
    this.sectionElements.changes.subscribe(() => {
      this.scrollToSection(this.$currentSectionId.value);
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

  deleteSection(section: Section) {
    const pages = this.pages();
    const page = pages[section.page_index]
    page.sections = page.sections.filter(s => s.id != section.id);
  }

  protected setEditingSection(isEditing: boolean) {
    this.isEditingSection.set(isEditing);
  }

  protected showOrHidePages(showPages: boolean) {
    this.isShowingPages.set(showPages);
  }

  protected setCurrentSectionId(sectionId: number) {
    this.$currentSectionId.next(sectionId);
    this.scrollToSection(sectionId);
  }

  protected deleteBookDialog(templateRef: TemplateRef<any>) {
    const dialogRef = this.dialog.open(templateRef);

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.deleteBook();
      }
    });
  }

  private deleteBook() {
    this.booksService.delete(this.bookId()).subscribe(
      () => {
        this.router.navigate(['/books']);
      }
    );
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
    return `${this.formatter.format(this.bookWithContent().stats.total_size_bytes / 1024 / 1024)}`;
  }

  protected downloadProgressPercent(): string {
    const info = this.downloadInfo();
    if (!info || info.fragments_total == 0) {
      return "0";
    } else {
      return `${this.formatter.format(info.fragments_downloaded / info.fragments_total * 100)}`;
    }
  }

  private reloadDownloadInfo() {
    this.downloadService.getDownloadInfo(this.bookId())
      .subscribe(val => this.downloadInfo.set(val));
  }

  protected setTheme(theme: string) {
    this.themeService.setTheme(theme == "dark");
  }
}
