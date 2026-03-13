import { Routes } from '@angular/router';
import { BooksPage } from './pages/books/books-page';
import { AddBookPage } from './pages/add-book/add-book-page';
import { ViewBookPage } from './pages/view-book-page/view-book-page';
import { authGuard } from './core/auth.guard';
import { EditBookPage } from './pages/edit-book-page/edit-book-page';

export const routes: Routes = [
  {path: 'books', component: BooksPage, canActivate: [authGuard]},
  {path: 'books/:bookId', component: ViewBookPage, canActivate: [authGuard]},
  {path: 'books/:bookId/edit', component: EditBookPage, canActivate: [authGuard]},
  {path: 'add-book', component: AddBookPage, canActivate: [authGuard]},
  {path: '**', redirectTo: '/books'}
];
