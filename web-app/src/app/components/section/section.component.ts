import { Component, input } from '@angular/core';
import { Section } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';

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

  getParagraphs() {
    return this.section().content.split('\n');
  }
}
