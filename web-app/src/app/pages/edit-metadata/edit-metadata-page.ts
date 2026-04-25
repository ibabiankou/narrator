import { Component, computed, inject, input, OnInit } from '@angular/core';
import { BreadcrumbContentDirective, ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { Title } from '@angular/platform-browser';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { filter, repeat, switchMap, take, tap, timer } from 'rxjs';
import { BookMetadata, BookStatus } from '../../core/models/books.dto';
import { BooksService } from '../../core/services/books.service';
import { AuthService } from '../../core/services/authService';
import { Router } from '@angular/router';
import { AsyncPipe, JsonPipe } from '@angular/common';
import { FileAsBlobPipe } from '../../core/fileAsBlobPipe';
import { BookDetailsForm } from '../../components/book-details-form/book-details-form';
import { BookOverview } from '../../components/book-overview/book-overview';

@Component({
  selector: 'app-edit-metadata-page',
  imports: [
    ToolbarComponent,
    BreadcrumbContentDirective,
    JsonPipe,
    AsyncPipe,
    FileAsBlobPipe,
    BookDetailsForm,
    BookOverview
  ],
  templateUrl: './edit-metadata-page.html',
  styleUrl: './edit-metadata-page.scss',
})
export class EditMetadataPage implements OnInit {
  private titleService: Title = inject(Title);
  private booksService = inject(BooksService);
  private authService: AuthService = inject(AuthService);
  private router: Router = inject(Router);

  readonly bookId = input.required<string>();
  readonly metadataForReview;
  readonly candidate;

  ngOnInit() {
    this.titleService.setTitle('Edit Details - NNarrator');
  }

  constructor() {
    this.metadataForReview = toSignal(toObservable(this.bookId).pipe(
      switchMap(id =>
        this.booksService.getBookMetadataForReview(id)
          .pipe(
            repeat({
              count: 25,
              delay: (count) => timer(2 ^ count * 500 * (0.75 + 0.5 * Math.random()))
            }),
            // TODO: Show a message to user if the book is in a wrong status? OR redirect it to a different page right away?
            filter((book) => BookStatus.ge(book.overview.status, BookStatus.ready_for_metadata_review)),
            take(1),
            tap(book => {
              if (!this.authService.isOwner(book.overview.owner_id)) {
                this.router.navigate(['/forbidden']);
              }
            })
          )
      )
    ));
    this.candidate = computed(() => {
      if (this.metadataForReview()?.metadata_candidates.candidates.length == 0) {
        return undefined;
      }
      return this.metadataForReview()?.metadata_candidates.candidates[0];
    });
  }

  protected submitReviewMetadata(bookMetadata: BookMetadata) {
    console.log("submitting review metadata", bookMetadata);
    this.booksService.updateBookMetadata(this.bookId(), bookMetadata)
      .subscribe({
        next: book => {
          this.router.navigate(['/books', book.id, 'edit']);
        },
        error: err => {
          console.error("Error: ", err);
        }
      })
  }
}
