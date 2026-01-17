import { Component, inject, model, OnInit } from '@angular/core';
import { MatFabButton, MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { Router, RouterLink } from '@angular/router';
import { BookOverview } from '../../core/models/books.dto';
import { MatToolbar } from '@angular/material/toolbar';
import { Title } from '@angular/platform-browser';
import { BooksService } from '../../core/services/books.service';

@Component({
  selector: 'app-books-page',
  imports: [
    MatIcon,
    MatFabButton,
    RouterLink,
    MatToolbar,
    MatIconButton
  ],
  templateUrl: './books-page.html',
  styleUrl: './books-page.scss',
})
export class BooksPage implements OnInit {

  router: Router = inject(Router)
  books = model.required<BookOverview[]>();

  constructor(private booksService: BooksService,
              private titleService: Title) {}

  ngOnInit() {
    this.titleService.setTitle('Books - NNarrator');
  }

  navigateToAdd() {
    this.router.navigate(['/add-book']);
  }

  protected deleteBook(id: string) {
    this.booksService.delete(id).subscribe(
      () => {
        this.books.set(this.books().filter(book => book.id !== id));
      }
    );
  }
}
