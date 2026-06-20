import { Component, computed, effect, inject, input, model } from '@angular/core';
import { ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { filter, switchMap } from 'rxjs';
import { BooksService } from '../../core/services/books.service';
import { ReadiumService } from '../../core/services/readium.service';
import { ReadiumEpub } from '../../components/readium-epub/readium-epub';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatSidenavModule } from '@angular/material/sidenav';
import { TocItem } from '../../core/models/books.dto';
import { MatButton, MatIconButton } from '@angular/material/button';
import { Router, RouterLink } from '@angular/router';
import { TocComponent } from '../../components/toc/toc.component';
import { MatIcon } from '@angular/material/icon';

@Component({
  selector: 'app-select-for-narration',
  imports: [
    ToolbarComponent,
    ReadiumEpub,
    MatSidenavModule,
    MatButton,
    TocComponent,
    MatIcon,
    MatIconButton,
    RouterLink,
  ],
  templateUrl: './select-for-narration.html',
  styleUrl: './select-for-narration.scss',
})
export class SelectForNarration {
  private booksService = inject(BooksService);
  private readiumService = inject(ReadiumService);
  private router: Router = inject(Router);

  bookId = input.required<string>();
  bookDetails = toSignal(toObservable(this.bookId).pipe(
    switchMap(bookId => this.booksService.getBookDetails(bookId))
  ));
  publication = toSignal(toObservable(this.bookDetails).pipe(
    filter(bookDetails => !!bookDetails),
    switchMap(bookDetails => {
      return this.readiumService.getPublication(bookDetails.book_file_key)
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

  protected startNarration() {
    this.booksService.startNarration(this.bookId(), this.tocItems()!).subscribe({
      next: value => {
        this.router.navigate(['/books', this.bookId()]);
      }
    });
  }
}
