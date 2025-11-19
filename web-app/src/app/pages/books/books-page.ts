import { Component, inject, input } from '@angular/core';
import { MatFabButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { Router, RouterLink } from '@angular/router';
import { BookDetails } from '../../core/models/books.dto';
import { MatToolbar } from '@angular/material/toolbar';

@Component({
  selector: 'app-books-page',
  imports: [
    MatIcon,
    MatFabButton,
    RouterLink,
    MatToolbar
  ],
  templateUrl: './books-page.html',
  styleUrl: './books-page.scss',
})
export class BooksPage {

  router: Router = inject(Router)
  books = input.required<BookDetails[]>();

  navigateToAdd() {
    this.router.navigate(['/add-book']);
  }
}
