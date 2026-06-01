import { Component, computed, inject, input, viewChild } from '@angular/core';
import { ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { filter, switchMap } from 'rxjs';
import { BooksService } from '../../core/services/books.service';
import { ReadiumService } from '../../core/services/readium.service';
import { ReadiumEpub } from '../../components/readium-epub/readium-epub';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatCheckbox, MatCheckboxChange } from '@angular/material/checkbox';
import { Link } from '@readium/shared';
import { TocItem } from '../../core/models/books.dto';

@Component({
  selector: 'app-select-for-narration',
  imports: [
    ToolbarComponent,
    ReadiumEpub,
    MatSidenavModule,
    MatCheckbox,
  ],
  templateUrl: './select-for-narration.html',
  styleUrl: './select-for-narration.scss',
})
export class SelectForNarration {
  private booksService = inject(BooksService);
  private readiumService = inject(ReadiumService);

  readonly readiumEpub = viewChild(ReadiumEpub);

  bookId = input.required<string>();
  bookDetails = toSignal(toObservable(this.bookId).pipe(
    switchMap(bookId => this.booksService.getBookDetails(bookId))
  ));
  publication = toSignal(toObservable(this.bookDetails).pipe(
    filter(bookDetails => !!bookDetails),
    switchMap(bookDetails => {
      return this.readiumService.getPublication(bookDetails.source_file_key)
    })));

  title = computed(() => this.bookDetails()?.title ?? "Loading...");

  tocItems = toSignal(toObservable(this.bookId).pipe(
    switchMap(bookId => this.booksService.getTableOfContent(bookId))
  ));

  protected navigate(item: TocItem) {
    console.log("Navigate to ", item);
    const link = new Link({href: item.href});
    this.readiumEpub()!.navigate(link);
  }

  protected toggleItem(item: TocItem, event: MatCheckboxChange) {
    // TODO: Implement "smarter" toggle logic.
    item.narrate = event.checked;
    console.log("Items: ", this.tocItems());
  }
}
