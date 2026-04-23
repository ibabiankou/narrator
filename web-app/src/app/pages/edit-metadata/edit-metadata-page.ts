import { Component, computed, inject, input, OnInit } from '@angular/core';
import { BreadcrumbContentDirective, ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { Title } from '@angular/platform-browser';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { filter, repeat, switchMap, take, tap, timer } from 'rxjs';
import { BookStatus } from '../../core/models/books.dto';
import { BooksService } from '../../core/services/books.service';
import { AuthService } from '../../core/services/authService';
import { Router } from '@angular/router';
import { AsyncPipe, JsonPipe } from '@angular/common';
import { FileAsBlobPipe } from '../../core/fileAsBlobPipe';
import { MatCard, MatCardActions, MatCardContent } from '@angular/material/card';
import { MatButton } from '@angular/material/button';
import { MatFormField, MatInput, MatLabel } from '@angular/material/input';
import { MatChipGrid, MatChipInput, MatChipRow } from '@angular/material/chips';
import { MatIcon } from '@angular/material/icon';

@Component({
  selector: 'app-edit-metadata-page',
  imports: [
    ToolbarComponent,
    BreadcrumbContentDirective,
    JsonPipe,
    AsyncPipe,
    FileAsBlobPipe,
    MatCard,
    MatCardContent,
    MatCardActions,
    MatButton,
    MatFormField,
    MatLabel,
    MatInput,
    MatChipGrid,
    MatChipRow,
    MatIcon,
    MatChipInput
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
            filter((book) => book.overview.status == BookStatus.ready_for_metadata_review),
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

}
