import { Component, effect, input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipInputEvent, MatChipsModule } from '@angular/material/chips';
import { MatInputModule } from '@angular/material/input';
import { MatIcon } from '@angular/material/icon';
import { BookMetadata } from '../../core/models/books.dto';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { AbstractControl, FormControl, ReactiveFormsModule, ValidationErrors } from '@angular/forms';


function cleanIsbn(value: string): string {
  if (!value) return '';
  return value.replace(/[^0-9X]/gi, '').toUpperCase();
}

@Component({
  selector: 'app-book-details-form',
  imports: [
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIcon,
    MatInputModule,
    ReactiveFormsModule
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

  readonly isbnControl = new FormControl<string>("", this.validateIsbnFormat);

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

  protected addAuthor($event: MatChipInputEvent) {
    const newItem = $event.value.trim();
    if (newItem.length > 0) {
      this.authors.push(newItem);
    }
    $event.chipInput!.clear();
  }

  protected removeAuthor(author: string) {
    this.authors = this.authors.filter(a => a !== author);
  }

  private validateIsbnFormat(control: AbstractControl<string>): ValidationErrors | null {
    if (!control.value) return null;
    const value = cleanIsbn(control.value);

    // 1. Basic length check
    if (value.length !== 10 && value.length !== 13) {
      return { invalidIsbn: 'Invalid length' };
    }

    // 2. ISBN-10 Checksum
    if (value.length === 10) {
      let sum = 0;
      for (let i = 0; i < 9; i++) {
        sum += parseInt(value[i]) * (10 - i);
      }
      const lastChar = value[9].toUpperCase();
      sum += (lastChar === 'X') ? 10 : parseInt(lastChar);

      const validIsbn10 = (sum % 11 === 0);
      return validIsbn10 ? null : { checksum: true };
    }

    // 3. ISBN-13 Checksum
    if (value.length === 13) {
      let sum = 0;
      for (let i = 0; i < 13; i++) {
        // Multiply every second digit by 3
        sum += parseInt(value[i]) * (i % 2 === 0 ? 1 : 3);
      }

      const validIsbn13 = (sum % 10 === 0);
      return validIsbn13 ? null : { checksum: true };
    }

    return null;
  }

  protected addIsbn(event: MatChipInputEvent): void {
    this.isbnControl.markAsTouched();

    if (this.isbnControl.invalid) return;

    const cleanedValue = cleanIsbn(event.value);
    if (cleanedValue.length === 0) return;

    if (this.isbns.includes(cleanedValue)) return;

    this.isbns.push(cleanedValue);
    event.chipInput!.clear();
    this.isbnControl.setValue('');
  }

  protected removeIsbn(isbn: string) {
    this.isbns = this.isbns.filter(i => i !== isbn);
  }
}
