import { Component, inject, model, output } from '@angular/core';
import { BookMetadata } from '../../core/models/books.dto';
import { MatButtonModule, MatIconButton } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent } from '@angular/material/dialog';
import { FileAsBlobPipe } from '../../core/fileAsBlobPipe';
import { AsyncPipe } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatLabel } from '@angular/material/input';


@Component({
  selector: 'app-book-details-dialog',
  imports: [
    AsyncPipe,
    FileAsBlobPipe,
    MatButtonModule,
    MatIconButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatIconModule,
    MatLabel
  ],
  templateUrl: './book-details-dialog.html',
  styleUrl: './book-details-dialog.scss',
})
export class BookDetailsDialog {
  readonly bookMetadata = inject<BookMetadata>(MAT_DIALOG_DATA);

  readonly onAdd = output<Partial<BookMetadata>>();

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

  protected addField(field: keyof BookMetadata) {
    const partial: Partial<BookMetadata> = { [field]: this.bookMetadata[field] };
    this.onAdd.emit(partial);
  }
}
