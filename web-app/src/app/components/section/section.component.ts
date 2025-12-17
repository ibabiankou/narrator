import { Component, input, output, signal } from '@angular/core';
import { Section } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { MatInput } from '@angular/material/input';
import { CdkTextareaAutosize } from '@angular/cdk/text-field';
import { SectionsService } from '../../core/services/sections.service';

@Component({
  selector: 'app-section',
  imports: [
    MatIcon,
    MatIconButton,
    MatInput,
    CdkTextareaAutosize
  ],
  templateUrl: './section.component.html',
  styleUrl: './section.component.scss',
})
export class SectionComponent {
  section = input.required<Section>();
  sectionDeleted = output();
  isEditing = signal(false)

  editingModeChanged = output<boolean>();

  constructor(private sectionsService: SectionsService) {
  }

  getParagraphs() {
    return this.section().content.split('\n');
  }

  deleteSection() {
    this.sectionsService.deleteSection(this.section().id)
      .subscribe({
        next: () => {
          this.sectionDeleted.emit();
        }
      })
  }

  editSection() {
    this.isEditing.set(true);
    this.editingModeChanged.emit(this.isEditing());
  }

  saveSection(value: string) {
    this.section().content = value;
    this.sectionsService.updateSection(this.section()).subscribe({
      next: () => {
        this.cancelEditing();
      }
    });
  }

  cancelEditing() {
    this.isEditing.set(false);
    this.editingModeChanged.emit(this.isEditing());
  }
}
