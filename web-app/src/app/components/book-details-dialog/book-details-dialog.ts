import { Component, effect, inject, model } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatInputModule } from '@angular/material/input';
import { BookMetadata } from '../../core/models/books.dto';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';


@Component({
  selector: 'app-book-details-dialog',
  imports: [
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    FormsModule
  ],
  templateUrl: './book-details-dialog.html',
  styleUrl: './book-details-dialog.scss',
})
export class BookDetailsDialog {
  readonly bookMetadata = inject<BookMetadata>(MAT_DIALOG_DATA);

  protected title = model<string>();
  protected series = model<string>();
  protected description = model<string>();
  protected authors = model<string[]>([]);
  protected isbns = model<string[]>([]);

  constructor() {
    effect(() => {
      const metadata = this.bookMetadata;

      this.title.set(metadata.title);
      this.series.set(metadata.series);
      this.description.set(metadata.description);
      this.authors.set([...metadata.authors]);
      this.isbns.set([...metadata.isbns]);
    });
  }

  // A dialog to display book cover along with details and controls to merge into main details.

  protected json() {
    return JSON.stringify(this.bookMetadata, null, 2);
  }
}
