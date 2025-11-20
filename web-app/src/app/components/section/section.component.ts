import { Component, input } from '@angular/core';
import { Section } from '../../core/models/books.dto';

@Component({
  selector: 'app-section',
  imports: [],
  templateUrl: './section.component.html',
  styleUrl: './section.component.scss',
})
export class SectionComponent {
  section = input.required<Section>();
}
