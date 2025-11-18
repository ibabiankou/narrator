import { Routes } from '@angular/router';
import { BooksPage } from './pages/books/books-page';
import { AddBookPage } from './pages/add-book/add-book-page';
import { ViewBookPage } from './pages/view-book-page/view-book-page';
import { bookContentResolver, bookResolver, booksResolver } from './core/resolvers';

export const routes: Routes = [
  {path: 'books', component: BooksPage, resolve: {books: booksResolver}},
  {path: 'books/:id', component: ViewBookPage, resolve: { book: bookResolver, pages: bookContentResolver }},
  {path: 'add-book', component: AddBookPage},
  {path: '**', redirectTo: '/books'}
];
