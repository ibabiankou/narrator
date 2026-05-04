import { Component, inject, output } from '@angular/core';
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

  readonly useOneField = output<Partial<BookMetadata>>();
  readonly useAllInfo = output<BookMetadata>();

  protected hasCover() {
    return this.bookMetadata.cover != undefined && this.bookMetadata.cover!.length > 0;
  }

  protected isCoverInternal() {
    const externalUrl = this.bookMetadata.cover?.startsWith("http");
    return this.hasCover() && !externalUrl;
  }

  protected addField(field: keyof BookMetadata) {
    const partial: Partial<BookMetadata> = {[field]: this.bookMetadata[field]};
    this.useOneField.emit(partial);
  }

  protected addAllDetails() {
    this.useAllInfo.emit(this.bookMetadata);
  }
}
