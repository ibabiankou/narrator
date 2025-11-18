import { SafeResourceUrl } from '@angular/platform-browser';

export interface CreateBookRequest {
  id: string;
  title: string;
  pdf_temp_file_id: string;
}

export interface BookDetails {
  id: string;
  title: string;
  pdf_file_name: string;
}

export interface Section {
  // Index of the section within the book.
  section_index: number;
  // Index of the page where the section starts.
  page_index: number;

  content: string;
}

export interface BookPage {
  // Index of the page within the book.
  index: number;
  // File name of the page. It can be used to download the page.
  file_name: string;

  file_url: SafeResourceUrl;

  // Sections of the book starting on this page.
  sections: Section[];
}

export interface BookContent {
  pages: BookPage[];
}
