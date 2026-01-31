import { Routes } from '@angular/router';
import { BooksPage } from './pages/books/books-page';
import { AddBookPage } from './pages/add-book/add-book-page';
import { ViewBookPage } from './pages/view-book-page/view-book-page';

export const routes: Routes = [
  {path: 'books', component: BooksPage},
  {path: 'books/:bookId', component: ViewBookPage},
  {path: 'add-book', component: AddBookPage},
  {path: '**', redirectTo: '/books'}
];
