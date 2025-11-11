import { Component } from '@angular/core';
import { MatFormField } from '@angular/material/form-field';
import { MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatButton } from '@angular/material/button';
import { FormsModule } from '@angular/forms';
import { MatCard, MatCardActions, MatCardContent, MatCardHeader, MatCardTitle } from '@angular/material/card';
import { Router } from '@angular/router';
import { FilesService } from '../../core/services/files.service';
import { switchMap } from 'rxjs';
import { BooksService } from '../../core/services/books.service';
import { v4 as uuidv4 } from 'uuid';

@Component({
  selector: 'app-add-book-page',
  imports: [
    MatFormField,
    MatLabel,
    MatInput,
    MatButton,
    FormsModule,
    MatCard,
    MatCardHeader,
    MatCardTitle,
    MatCardContent,
    MatCardActions
  ],
  templateUrl: './add-book-page.html',
  styleUrl: './add-book-page.scss',
})
export class AddBookPage {
  title: string = '';
  file: File | null = null;
  fileName = '';

  constructor(private router: Router,
              private filesService: FilesService,
              private booksService: BooksService) {
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.file = file;
      this.fileName = file.name;
    }
  }

  navigateToBooks() {
    this.router.navigate(['/books']);
  }

  addBook() {
    console.log('addBook');
    this.filesService.uploadFile(this.file!)
      .pipe(switchMap(tempFile => {
        console.log('tempFile: ', tempFile);
        return this.booksService.createBook({
          "id": uuidv4(),
          "title": this.title,
          "pdf_temp_file_id": tempFile.id
        });
      }))
      .subscribe({
        next: bookDetails => {
          console.log("Book details: ", bookDetails);
          this.router.navigate(['/books', bookDetails.id]);
        },
        error: err => {
          // TODO: show the error message.
          console.log("Error: ", err);
        }
      })
  }
}
