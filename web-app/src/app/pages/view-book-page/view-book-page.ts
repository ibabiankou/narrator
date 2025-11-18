import { Component, inject, input } from '@angular/core';
import { BookDetails, BookPage } from '../../core/models/books.dto';
import { environment } from '../../../environments/environment';
import { DomSanitizer } from '@angular/platform-browser';

@Component({
  selector: 'app-view-book-page',
  imports: [],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage {
  private sanitizer = inject(DomSanitizer);

  book = input.required<BookDetails>();
  pages = input.required<BookPage[]>();

  pageUrl(id: string, file_name: string) {
    const url = `${environment.api_base_url}/books/${id}/pages/${file_name}#toolbar=0&navpanes=0&scrollbar=0`
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }
}
