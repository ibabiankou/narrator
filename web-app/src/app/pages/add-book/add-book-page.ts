import { Component, OnInit } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatButton } from '@angular/material/button';
import { FormsModule } from '@angular/forms';
import { MatCard, MatCardActions, MatCardContent, MatCardHeader, MatCardTitle } from '@angular/material/card';
import { Router } from '@angular/router';
import { FilesService } from '../../core/services/files.service';
import { switchMap } from 'rxjs';
import { BooksService } from '../../core/services/books.service';
import { v4 as uuidv4 } from 'uuid';
import { Title } from '@angular/platform-browser';
import { BreadcrumbContentDirective, ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { MatSlideToggle } from '@angular/material/slide-toggle';

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
    MatCardActions,
    ToolbarComponent,
    BreadcrumbContentDirective,
    MatSlideToggle
  ],
  templateUrl: './add-book-page.html',
  styleUrl: './add-book-page.scss',
})
export class AddBookPage implements OnInit {
  title: string = '';
  file: File | null = null;
  fileName = '';
  shared = true;

  constructor(private router: Router,
              private filesService: FilesService,
              private booksService: BooksService,
              private titleService: Title) {
  }

  ngOnInit() {
    this.titleService.setTitle('Add Book - NNarrator');
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
    this.filesService.uploadFile(this.file!)
      .pipe(switchMap(tempFile => {
        return this.booksService.createBook({
          "id": uuidv4(),
          "title": this.title,
          "pdf_temp_file_id": tempFile.id,
          "shared": this.shared
        });
      }))
      .subscribe({
        next: bookDetails => {
          this.router.navigate(['/books', bookDetails.id, 'edit']);
        },
        error: err => {
          // TODO: show the error message.
          console.error("Error: ", err);
        }
      })
  }
}
