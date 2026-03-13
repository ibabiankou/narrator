import { Component, computed, inject, input, model, TemplateRef, } from '@angular/core';
import { BookStatus, Section } from '../../core/models/books.dto';
import { BooksService } from '../../core/services/books.service';
import { filter, repeat, switchMap, take, tap, timer } from 'rxjs';
import { MatIcon } from '@angular/material/icon';
import { Router, RouterLink } from '@angular/router';
import { SectionComponent } from '../../components/section/section.component';
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
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';
import { MatButtonToggle, MatButtonToggleGroup } from '@angular/material/button-toggle';
import { ThemeService } from '../../core/services/theme.service';
import { SettingsService } from '../../core/services/settings.service';
import { BookPage } from '../../components/book-page/book-page';
import { VisibilityDirective } from '../../core/visibilityDirective';

@Component({
  selector: 'app-view-book-page',
  imports: [
    MatIcon,
    SectionComponent,
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
    BookPage,
    VisibilityDirective,
    RouterLink,
  ],
  templateUrl: './edit-book-page.html',
  styleUrl: './edit-book-page.scss',
})
export class EditBookPage {
  private booksService = inject(BooksService);
  private titleService = inject(Title);
  private dialog = inject(MatDialog);
  private router: Router = inject(Router);
  private settingsService: SettingsService = inject(SettingsService);
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

  settings = toSignal(this.settingsService.userPreferences$);

  isEditingSection = model(false);
  isShowingPages = computed(() => this.settings()!["viewer_mode"] === "both");

  deleteSection(section: Section) {
    const pages = this.pages();
    const page = pages[section.page_index]
    page.sections = page.sections.filter(s => s.id != section.id);
  }

  protected setEditingSection(isEditing: boolean) {
    this.isEditingSection.set(isEditing);
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

  protected setTheme(theme: string) {
    this.themeService.setTheme(theme);
    this.settingsService.patch("user_preferences", {theme: theme}).subscribe();
  }
}
