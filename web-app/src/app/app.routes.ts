import { Routes } from '@angular/router';
import { BooksPage } from './pages/books/books-page';
import { AddBookPage } from './pages/add-book/add-book-page';
import { ViewBookPage } from './pages/view-book-page/view-book-page';
import { bookResolver } from './core/resolvers';

export const routes: Routes = [
  {path: 'books', component: BooksPage},
  {path: 'books/:id', component: ViewBookPage, resolve: { book: bookResolver }},
  {path: 'books/add', component: AddBookPage},
  {path: '**', redirectTo: '/books'}
];
