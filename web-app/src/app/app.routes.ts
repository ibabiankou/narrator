import { Routes } from '@angular/router';
import { BooksPage } from './pages/books/books-page';
import { ViewBookPage } from './pages/view-book-page/view-book-page';
import { authGuard } from './core/auth.guard';
import { ForbiddenPage } from './pages/forbidden/forbidden-page';
import { EditMetadataPage } from './pages/edit-metadata/edit-metadata-page';
import { SelectForNarration } from './pages/select-for-narration/select-for-narration';

export const routes: Routes = [
  {path: 'books', component: BooksPage, canActivate: [authGuard]},
  {path: 'books/:bookId', component: ViewBookPage, canActivate: [authGuard]},
  {path: 'books/:bookId/select-for-narration', component: SelectForNarration, canActivate: [authGuard]},
  {path: 'books/:bookId/edit-details', component: EditMetadataPage, canActivate: [authGuard]},
  {path: 'forbidden', component: ForbiddenPage},
  {path: '**', redirectTo: '/books'}
];
