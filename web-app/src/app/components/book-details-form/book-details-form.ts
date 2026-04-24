import { Component, effect, input } from '@angular/core';
import { MatButton } from '@angular/material/button';
import { MatCard, MatCardActions, MatCardContent } from '@angular/material/card';
import { MatChipGrid, MatChipInput, MatChipRow } from '@angular/material/chips';
import { MatFormField, MatInput, MatLabel } from '@angular/material/input';
import { MatIcon } from '@angular/material/icon';
import { BookMetadata } from '../../core/models/books.dto';

@Component({
  selector: 'app-book-details-form',
  imports: [
    MatButton,
    MatCard,
    MatCardActions,
    MatCardContent,
    MatChipGrid,
    MatChipInput,
    MatChipRow,
    MatFormField,
    MatIcon,
    MatInput,
    MatLabel
  ],
  templateUrl: './book-details-form.html',
  styleUrl: './book-details-form.scss',
})
export class BookDetailsForm {

  protected readonly bookMetadata = input.required<BookMetadata>();

  protected title?: string;
  protected series?: string;
  protected description?: string;
  protected authors: string[] = [];
  protected isbns: string[] = [];

  constructor() {
    effect(() => {
      const metadata = this.bookMetadata();

      this.title = metadata.title;
      this.series = metadata.series;
      this.description = metadata.description;
      this.authors = metadata.authors;
      this.isbns = metadata.isbns;
    });
  }

}
