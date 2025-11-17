import { RedirectCommand, ResolveFn, Router } from '@angular/router';
import { BookDetails } from './models/books.dto';
import { inject } from '@angular/core';
import { BooksService } from './services/books.service';
import { catchError, of } from 'rxjs';

export const bookResolver: ResolveFn<BookDetails | RedirectCommand> = (route) => {
  console.log('bookResolver');
  const booksService = inject(BooksService);
  const router = inject(Router);
  const bookId = route.paramMap.get('id')!;
  return booksService.getBook(bookId).pipe(
    catchError(error => {
      console.error('Failed to load book details:', error);
      return of(new RedirectCommand(router.parseUrl('/books')));
    })
  );
};
