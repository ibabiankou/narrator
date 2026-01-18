import { Component, inject, model, OnInit } from '@angular/core';
import { MatFabButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { Router, RouterLink } from '@angular/router';
import { BookOverview } from '../../core/models/books.dto';
import { MatToolbar } from '@angular/material/toolbar';
import { Title } from '@angular/platform-browser';

@Component({
  selector: 'app-books-page',
  imports: [
    MatIcon,
    MatFabButton,
    RouterLink,
    MatToolbar,
  ],
  templateUrl: './books-page.html',
  styleUrl: './books-page.scss',
})
export class BooksPage implements OnInit {

  private router: Router = inject(Router);
  books = model.required<BookOverview[]>();

  constructor(private titleService: Title) {}

  ngOnInit() {
    this.titleService.setTitle('Books - NNarrator');
  }

  navigateToAdd() {
    this.router.navigate(['/add-book']);
  }
}
