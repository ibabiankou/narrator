import { Component, computed, inject, input, model, Signal, TemplateRef, } from '@angular/core';
import { BookPage, BookStatus, BookWithContent, Section } from '../../core/models/books.dto';
import { BooksService } from '../../core/services/books.service';
import { EMPTY, filter, repeat, switchMap, take, tap, timer } from 'rxjs';
import { Router, RouterLink } from '@angular/router';
import { SectionComponent } from '../../components/section/section.component';
import { Title } from '@angular/platform-browser';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import {
  ActionButtonContentDirective,
  BreadcrumbContentDirective,
  ToolbarComponent
} from '../../components/toolbar/toolbar.component';
import { SettingsService } from '../../core/services/settings.service';
import { PdfPage } from '../../components/pdf-page/pdf-page';
import { VisibilityDirective } from '../../core/visibilityDirective';
import { AuthService } from '../../core/services/authService';
import { BookMenu } from '../../components/book-menu/book-menu/book-menu';
import { MatIcon } from '@angular/material/icon';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatTooltip } from '@angular/material/tooltip';
import {
  MatDialog,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogTitle
} from '@angular/material/dialog';

@Component({
  selector: 'app-view-book-page',
  imports: [
    SectionComponent,
    SkeletonComponent,
    ToolbarComponent,
    BreadcrumbContentDirective,
    ActionButtonContentDirective,
    PdfPage,
    VisibilityDirective,
    RouterLink,
    BookMenu,
    MatIcon,
    MatIconButton,
    MatTooltip,
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle,
  ],
  templateUrl: './edit-book-page.html',
  styleUrl: './edit-book-page.scss',
})
export class EditBookPage {
  private booksService = inject(BooksService);
  private titleService = inject(Title);
  private router: Router = inject(Router);
  private settingsService: SettingsService = inject(SettingsService);
  private authService: AuthService = inject(AuthService);
  private dialog = inject(MatDialog);

  bookId = input.required<string>();

  bookWithContent: Signal<BookWithContent>;
  pages: Signal<BookPage[]>;

  settings = toSignal(this.settingsService.userPreferences$);

  isEditingSection = model(false);
  isShowingPages = computed(() => this.settings()!["viewer_mode"] === "both");

  constructor() {
    const bookWithContent$ = toObservable(this.bookId).pipe(
      switchMap(id =>
        this.booksService.getBookWithContent(id)
          .pipe(
            repeat({
              count: 25,
              delay: (count) => timer(2 ^ count * 300 * (0.75 + 0.5 * Math.random()))
            }),
            // TODO: Show a message to user if the book is in a wrong status? OR redirect it to a different page right away?
            filter((book) => BookStatus.ge(book.overview.status, BookStatus.ready_for_content_review)),
            take(1),
            tap(book => this.titleService.setTitle(`${book.overview.title} - NNarrator`)),
            tap(book => {
              if (!this.authService.isOwner(book.overview.owner_id)) {
                this.router.navigate(['/forbidden']);
              }
            })
          )
      ),
    );
    const bookWithContentSignal = toSignal(bookWithContent$);
    this.bookWithContent = computed(() => bookWithContentSignal()!);
    this.pages = computed(() => this.bookWithContent().pages);
  }

  deleteSection(section: Section) {
    const pages = this.pages();
    const page = pages[section.page_index]
    page.sections = page.sections.filter(s => s.id != section.id);
  }

  protected setEditingSection(isEditing: boolean) {
    this.isEditingSection.set(isEditing);
  }

  protected copyBookTitle() {
    navigator.clipboard.writeText(this.bookWithContent()?.overview.title ?? "");
  }

  protected openNarrateDialog(templateRef: TemplateRef<any>) {
    const dialogRef = this.dialog.open(templateRef);

    dialogRef.afterClosed()
      .pipe(switchMap(result => {
        if (result) {
          return this.booksService.enqueue(this.bookId());
        } else {
          return EMPTY;
        }
      }))
      .subscribe({
        next: () => {
          // TODO: Navigate to the book queue page.
          this.router.navigate(['/books', this.bookId()]);
        }
      });
  }

  protected showNarrateButton() {
    return this.bookWithContent()?.overview.status == BookStatus.ready_for_content_review;
  }
}
