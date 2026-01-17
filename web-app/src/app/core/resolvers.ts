import { RedirectCommand, ResolveFn, Router } from '@angular/router';
import { BookDetails, BookPage, Playlist } from './models/books.dto';
import { inject } from '@angular/core';
import { BooksService } from './services/books.service';
import { catchError, map, of } from 'rxjs';
import { PlaylistsService } from './services/playlists.service';

export const bookResolver: ResolveFn<BookDetails | RedirectCommand> = (route) => {
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

export const booksResolver: ResolveFn<BookDetails[]> = (route) => {
  const booksService = inject(BooksService);
  // TODO: consider adding pagination
  return booksService.listBooks().pipe(
    catchError(error => {
      console.error('Failed to load books:', error);
      return of([]);
    })
  );
};

export const bookContentResolver: ResolveFn<BookPage[]> = (route) => {
  const booksService = inject(BooksService);
  const bookId = route.paramMap.get('id')!;
  return booksService.getBookContent(bookId).pipe(
    map(content => content.pages),
    catchError(error => {
      console.error('Failed to load book content:', error);
      return of([]);
    })
  );
};

export const playbackProgressResolver: ResolveFn<Playlist> = (route) => {
  const service = inject(PlaylistsService);
  const bookId = route.paramMap.get('id')!;
  return service.getPlaylist(bookId).pipe(
    catchError(error => {
      console.error('Failed to load book playlist:', error);
      return of();
    })
  );
};
