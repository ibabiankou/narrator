import { AfterViewInit, Component, computed, effect, inject, input, model, OnInit, viewChild } from '@angular/core';
import { BookStatus, TocItem } from '../../core/models/books.dto';
import { BooksService } from '../../core/services/books.service';
import { filter, switchMap, take } from 'rxjs';
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
import { BookMenu } from '../../components/book-menu/book-menu/book-menu';
import { RouterLink } from '@angular/router';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { MatTooltip } from '@angular/material/tooltip';
import { SettingsService } from '../../core/services/settings.service';
import { ReadiumEpub } from '../../components/readium-epub/readium-epub';
import { ReadiumService } from '../../core/services/readium.service';

@Component({
  selector: 'app-view-book-page',
  imports: [
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
    ReadiumEpub,
  ],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage implements OnInit, AfterViewInit {
  private booksService = inject(BooksService);
  private readiumService = inject(ReadiumService);
  private settingsService = inject(SettingsService);
  private titleService = inject(Title);

  bookId = input.required<string>();

  readonly readiumEpub = viewChild(ReadiumEpub);

  bookDetails = toSignal(toObservable(this.bookId).pipe(
    switchMap(bookId => this.booksService.getBookDetails(bookId))
  ));
  publication = toSignal(toObservable(this.bookDetails).pipe(
    filter(bookDetails => !!bookDetails),
    switchMap(bookDetails => {
      return this.readiumService.getPublication(bookDetails.source_file_key)
    })));

  title = computed(() => this.bookDetails()?.title ?? "Loading...");

  tocItems = model<TocItem[]>();
  currentItem = 0;

  constructor() {
    effect(() => {
      this.booksService.getTableOfContent(this.bookId()).subscribe({
        next: tocItems => {
          this.tocItems.set(tocItems);
        },
      });
    });
  }


  ngOnInit() {
    this.settingsService.userPreferences$
      .pipe(take(1))
      .subscribe(preferences => {
        // this.settingsService.setFontSizeStyle(preferences["text_size"]);
        // TODO: make readium component aware of settings.
      });
  }

  ngAfterViewInit() {
  }

  protected copyBookTitle() {
    navigator.clipboard.writeText(this.title() ?? "");
  }

  protected readonly BookStatus = BookStatus;
}
