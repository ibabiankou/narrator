import { Component, effect, inject, input, model, output, signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipInputEvent, MatChipsModule } from '@angular/material/chips';
import { MatInputModule } from '@angular/material/input';
import { MatIcon } from '@angular/material/icon';
import { BookMetadata } from '../../core/models/books.dto';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, ValidationErrors } from '@angular/forms';
import { AsyncPipe } from '@angular/common';
import { FileAsBlobPipe } from '../../core/fileAsBlobPipe';
import { NotificationService } from '../../core/services/notificationService';
import { BooksService } from '../../core/services/books.service';


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
    ReactiveFormsModule,
    FormsModule,
    AsyncPipe,
    FileAsBlobPipe
  ],
  templateUrl: './book-details-form.html',
  styleUrl: './book-details-form.scss',
})
export class BookDetailsForm {
  private bookService = inject(BooksService);
  private notificationService = inject(NotificationService);

  readonly bookId = input.required<string>();
  readonly bookMetadata = input.required<BookMetadata>();
  reviewedMetadata = output<BookMetadata>();

  protected cover = model<string>();
  protected title = model<string>();
  protected series = model<string>();
  protected description = model<string>();
  protected authors = model<string[]>([]);
  protected isbns = model<string[]>([]);

  protected refreshTrigger = signal("");

  readonly isbnControl = new FormControl<string>("", this.validateIsbnFormat);

  constructor() {
    effect(() => {
      const metadata = this.bookMetadata();
      if (!metadata) return;

      this.cover.set(metadata.cover);
      this.title.set(metadata.title);
      this.series.set(metadata.series);
      this.description.set(metadata.description);
      this.authors.set([...metadata.authors]);
      this.isbns.set([...metadata.isbns]);
    });
  }

  protected addAuthor($event: MatChipInputEvent) {
    this.doAddAuthor($event.value.trim());
    $event.chipInput!.clear();
  }

  private doAddAuthor(author: string) {
    if (author.length > 0) {
      if (this.authors().includes(author)) return;
      this.authors.set([...this.authors(), author]);
    }
  }

  protected removeAuthor(author: string) {
    this.authors.set(this.authors().filter(a => a !== author));
  }

  private validateIsbnFormat(control: AbstractControl<string>): ValidationErrors | null {
    if (!control.value) return null;
    const value = cleanIsbn(control.value);

    // 1. Basic length check
    if (value.length !== 10 && value.length !== 13) {
      return {invalidIsbn: 'Invalid length'};
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
      return validIsbn10 ? null : {checksum: true};
    }

    // 3. ISBN-13 Checksum
    if (value.length === 13) {
      let sum = 0;
      for (let i = 0; i < 13; i++) {
        // Multiply every second digit by 3
        sum += parseInt(value[i]) * (i % 2 === 0 ? 1 : 3);
      }

      const validIsbn13 = (sum % 10 === 0);
      return validIsbn13 ? null : {checksum: true};
    }

    return null;
  }

  protected addIsbn(event: MatChipInputEvent): void {
    this.isbnControl.markAsTouched();
    if (this.isbnControl.invalid) return;

    this.doAddIsbn(event.value);

    event.chipInput!.clear();
    this.isbnControl.setValue('');
  }

  private doAddIsbn(isbn: string) {
    const cleanedValue = cleanIsbn(isbn);
    if (cleanedValue.length === 0) return;
    if (this.isbns().includes(cleanedValue)) return;
    this.isbns.set([...this.isbns(), cleanedValue]);
  }

  protected removeIsbn(isbn: string) {
    this.isbns.set(this.isbns().filter(i => i !== isbn));
  }

  protected emitReviewedMetadata() {
    const metadata: BookMetadata = {
      cover: this.cover(),
      title: this.title(),
      series: this.series(),
      description: this.description(),
      authors: this.authors(),
      isbns: this.isbns(),
    };
    this.reviewedMetadata.emit(metadata);
  }

  update(data: Partial<BookMetadata>) {
    const {isbns, authors, cover, title, series, description} = data;

    if (isbns && isbns.length > 0) {
      isbns.forEach(isbn => this.doAddIsbn(isbn));
    }
    if (authors && authors.length > 0) {
      authors.forEach(author => this.doAddAuthor(author));
    }
    if (cover) {
      this.cover.set(cover);
    }
    if (title) {
      this.title.set(title);
    }
    if (series) {
      this.series.set(series);
    }
    if (description) {
      this.description.set(description);
    }
  }

  protected goodreadsUrl() {
    var query = "";
    if (this.title()) {
      query += this.title() + " ";
    }
    if (this.authors().length > 0) {
      query += this.authors().join(" ");
    }
    return `https://www.goodreads.com/search?q=${query}`;
  }

  protected async selectCover() {
    const pickerOptions = {
      startIn: "downloads",
      types: [
        {
          description: "Images",
          accept: {
            "image/jpg": [".jpg", ".jpeg"],
            "image/png": [".png"],
            "image/webp": [".webp"],
          },
        },
      ],
      excludeAcceptAllOption: true,
      multiple: false,
    };
    const [fileHandle]: FileSystemFileHandle[] = await (window as any).showOpenFilePicker(pickerOptions);
    const file = await fileHandle.getFile();
    this.uploadCover(file);
  }

  private uploadCover(file: File) {
    if (file.size > 5 * 1024 * 1024) {
      this.notificationService.showError("Selected file is too large. Maximum size is 5MB.");
      return;
    }
    this.notificationService.showMessage(`Uploading '${file.name}'...`);

    return this.bookService.uploadCover(this.bookId(), file)
      .subscribe({
        next: coverPath => {
          this.notificationService.dismiss();
          this.cover.set(coverPath);
          this.refreshTrigger.set(`#v${Date.now()}`);
        }
      });
  }
}
