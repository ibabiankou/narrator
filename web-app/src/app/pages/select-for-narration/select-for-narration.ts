import { Component, effect, inject, input, model } from '@angular/core';
import { ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { switchMap, tap } from 'rxjs';
import { BooksService } from '../../core/services/books.service';
import { ReadiumService } from '../../core/services/readium.service';

@Component({
  selector: 'app-select-for-narration',
  imports: [
    ToolbarComponent,
  ],
  templateUrl: './select-for-narration.html',
  styleUrl: './select-for-narration.scss',
})
export class SelectForNarration {
  private booksService = inject(BooksService);
  private readiumService = inject(ReadiumService);

  bookId = input.required<string>();

  title = model<string>("");

  constructor() {
    effect(() => {
      // Fetch book overview.
      this.booksService.getBookDetails(this.bookId()).pipe(
        // Switch to publication.
        switchMap(bookDetails => this.readiumService.getPublication(bookDetails.source_file_key)),
        tap(publication => {
          const lang = publication.metadata.languages![0];
          this.title.set(publication.metadata.title.getTranslation(lang));
        })
        // TODO Render the book.
      ).subscribe();
    });
  }
}
