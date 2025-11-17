import { Component, input } from '@angular/core';
import { BookDetails } from '../../core/models/books.dto';

@Component({
  selector: 'app-view-book-page',
  imports: [],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage {
  book = input.required<BookDetails>();
}
