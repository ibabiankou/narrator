import { Component, inject, model, OnInit, signal } from '@angular/core';
import { BookDetails, BookPage, BookStatus } from '../../core/models/books.dto';
import { InfiniteScrollDirective } from 'ngx-infinite-scroll';
import { BooksService } from '../../core/services/books.service';
import { filter, repeat, switchMap, take, tap, timer } from 'rxjs';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { MatIcon } from '@angular/material/icon';
import { MatToolbar } from '@angular/material/toolbar';
import { RouterLink } from '@angular/router';
import { SectionComponent } from '../../components/section/section.component';

@Component({
  selector: 'app-view-book-page',
  imports: [
    InfiniteScrollDirective,
    MatProgressSpinner,
    MatIcon,
    MatToolbar,
    RouterLink,
    SectionComponent
  ],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage implements OnInit {
  private booksService = inject(BooksService);

  book = model.required<BookDetails>();
  pages = model.required<BookPage[]>();

  isLoading = signal(true);

  ngOnInit() {
    const book = this.book();
    const bookIsNotReady = book.status != BookStatus.ready;
    this.isLoading.set(bookIsNotReady);
    if (bookIsNotReady) {
      // Poll book status until it is ready. Use exponential backoff between retries.
      // Once it's ready, fetch the book content.
      this.booksService.getBook(book.id)
        .pipe(
          // Exponential backoff between retries.
          repeat({
            count: 25,
            delay: (count) => timer(2 ^ count * 300 * (0.75 + 0.5 * Math.random()))
          }),
          filter((book) => book.status == BookStatus.ready),
          tap(book => this.book.set(book)),
          take(1),
          switchMap((book) => this.booksService.getBookContent(book.id))
        ).subscribe(
        (content) => {
          this.pages.set(content.pages);
          this.isLoading.set(false);
        }
      );
    }
  }

  loadMorePages() {
    const bookId = this.book().id;
    const pages = this.pages()

    this.booksService.getBookContent(bookId, pages[pages.length - 1].index).subscribe(
      content => {
        this.pages.set([...pages, ...content.pages]);
      }
    );
  }
}
