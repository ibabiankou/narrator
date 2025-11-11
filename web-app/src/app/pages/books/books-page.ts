import { Component } from '@angular/core';
import { MatFabButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { Router } from '@angular/router';

@Component({
  selector: 'app-books-page',
  imports: [
    MatIcon,
    MatFabButton
  ],
  templateUrl: './books-page.html',
  styleUrl: './books-page.scss',
})
export class BooksPage {

  constructor(private router: Router) {
  }

  navigateToAdd() {
    this.router.navigate(['/books/add']);
  }
}
