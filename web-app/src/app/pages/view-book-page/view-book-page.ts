import { Component, inject, input, model } from '@angular/core';
import { BookDetails, BookPage } from '../../core/models/books.dto';
import { InfiniteScrollDirective } from 'ngx-infinite-scroll';
import { BooksService } from '../../core/services/books.service';

@Component({
  selector: 'app-view-book-page',
  imports: [
    InfiniteScrollDirective
  ],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage {

  private booksService = inject(BooksService);

  book = input.required<BookDetails>();
  pages = model.required<BookPage[]>();

  loadMorePages() {
    const bookId = this.book().id;
    const pages = this.pages()

    console.log("Loading more pages...");
    this.booksService.getBookContent(bookId, pages[pages.length-1].index).subscribe(
      content => {
        console.log("Adding more pages...");
        this.pages.set([...pages, ...content.pages]);
      }
    );
  }
}
