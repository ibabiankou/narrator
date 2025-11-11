import { Routes } from '@angular/router';
import { BooksPage } from './pages/books/books-page';
import { AddBookPage } from './pages/add-book/add-book-page';

export const routes: Routes = [
  {path: 'books', component: BooksPage},
  {path: 'books/add', component: AddBookPage},
  {path: '**', redirectTo: '/books'}
];
