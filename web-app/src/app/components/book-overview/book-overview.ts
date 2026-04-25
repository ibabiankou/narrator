import { Component, effect, input, model } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatInputModule } from '@angular/material/input';
import { BookMetadata } from '../../core/models/books.dto';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';


@Component({
  selector: 'app-book-overview',
  imports: [
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    FormsModule
  ],
  templateUrl: './book-overview.html',
  styleUrl: './book-overview.scss',
})
export class BookOverview {

  readonly bookMetadata = input.required<BookMetadata>();

  protected title = model<string>();
  protected series = model<string>();
  protected description = model<string>();
  protected authors = model<string[]>([]);
  protected isbns = model<string[]>([]);

  tintStyle = {"filter": `sepia(${80 + Math.floor(Math.random() * 30)}%) saturate(${60 + Math.floor(Math.random() * 90)}%) hue-rotate(${Math.floor(Math.random() * 360)}deg)`};

  constructor() {
    effect(() => {
      const metadata = this.bookMetadata();
      if (!metadata) return;

      this.title.set(metadata.title);
      this.series.set(metadata.series);
      this.description.set(metadata.description);
      this.authors.set([...metadata.authors]);
      this.isbns.set([...metadata.isbns]);
    });
  }

}
