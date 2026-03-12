import { Component, inject, OnInit } from '@angular/core';
import { MatFabButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { Router, RouterLink } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { toSignal } from '@angular/core/rxjs-interop';
import { BooksService } from '../../core/services/books.service';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import { ActionButtonContentDirective, ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { MatFormField, MatInput } from '@angular/material/input';
import { BehaviorSubject, take } from 'rxjs';
import { BookOverview } from '../../core/models/books.dto';

@Component({
  selector: 'app-books-page',
  imports: [
    MatIcon,
    MatFabButton,
    RouterLink,
    SkeletonComponent,
    ToolbarComponent,
    ActionButtonContentDirective,
    MatFormField,
    MatInput,
  ],
  templateUrl: './books-page.html',
  styleUrl: './books-page.scss',
})
export class BooksPage implements OnInit {
  private titleService = inject(Title);
  private router: Router = inject(Router);
  private bookService = inject(BooksService);

  private $books = new BehaviorSubject<BookOverview[]>([]);
  books = toSignal(this.$books);

  constructor() {
    this.bookService.listBooks().pipe(take(1)).subscribe(books => {
      this.$books.next(books);
    })
  }

  ngOnInit() {
    this.titleService.setTitle('Books - NNarrator');
  }

  navigateToAdd() {
    this.router.navigate(['/add-book']);
  }

  protected search($event: any) {
    this.bookService.searchBooks($event.target.value).pipe(take(1)).subscribe(books => {
      this.$books.next(books);
    });
  }
}
