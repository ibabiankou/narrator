import { ResolveFn } from '@angular/router';
import { BookOverview } from './models/books.dto';
import { inject } from '@angular/core';
import { BooksService } from './services/books.service';
import { catchError, of } from 'rxjs';

export const booksResolver: ResolveFn<BookOverview[]> = (route) => {
  const booksService = inject(BooksService);
  // TODO: consider adding pagination
  return booksService.listBooks().pipe(
    catchError(error => {
      console.error('Failed to load books:', error);
      return of([]);
    })
  );
};
