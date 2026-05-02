import { Component, inject, model } from '@angular/core';
import { BookMetadata } from '../../core/models/books.dto';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent } from '@angular/material/dialog';
import { FileAsBlobPipe } from '../../core/fileAsBlobPipe';
import { AsyncPipe } from '@angular/common';
import { MatLabel } from '@angular/material/input';


@Component({
  selector: 'app-book-details-dialog',
  imports: [
    AsyncPipe,
    FileAsBlobPipe,
    MatButtonModule,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatLabel
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
    const metadata = this.bookMetadata;

    this.title.set(metadata.title);
    this.series.set(metadata.series);
    this.description.set(metadata.description);
    this.authors.set([...metadata.authors]);
    this.isbns.set([...metadata.isbns]);
  }

  protected hasCover() {
    return this.bookMetadata.cover != undefined && this.bookMetadata.cover!.length > 0;
  }

  protected isCoverInternal() {
    const externalUrl = this.bookMetadata.cover?.startsWith("http");
    return this.hasCover() && !externalUrl;
  }
}
