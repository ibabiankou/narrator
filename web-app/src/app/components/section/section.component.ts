import { Component, input, output } from '@angular/core';
import { Section } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { BooksService } from '../../core/services/books.service';

@Component({
  selector: 'app-section',
  imports: [
    MatIcon,
    MatIconButton
  ],
  templateUrl: './section.component.html',
  styleUrl: './section.component.scss',
})
export class SectionComponent {
  section = input.required<Section>();
  sectionDeleted = output();

  constructor(private bookService: BooksService) {
  }

  getParagraphs() {
    return this.section().content.split('\n');
  }

  deleteSection() {
    this.bookService.deleteSection(this.section().book_id, this.section().id)
      .subscribe({
        next: () => {
          this.sectionDeleted.emit();
        }
      })
  }
}
