import { Component, input, output, signal } from '@angular/core';
import { Section } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { MatInput } from '@angular/material/input';
import { CdkTextareaAutosize } from '@angular/cdk/text-field';
import { SectionsService } from '../../core/services/sections.service';
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';

@Component({
  selector: 'app-section',
  imports: [
    MatIcon,
    MatIconButton,
    MatInput,
    CdkTextareaAutosize,
    MatMenuTrigger,
    MatMenu,
    MatMenuItem
  ],
  templateUrl: './section.component.html',
  styleUrl: './section.component.scss',
})
export class SectionComponent {
  section = input.required<Section>();
  sectionDeleted = output();
  isEditing = signal(false)

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
  }

  saveSection(value: string) {
    this.section().content = value;
    this.sectionsService.updateSection(this.section()).subscribe({
      next: () => {
        this.isEditing.set(false);
      }
    });
  }

  cancelEditing() {
    this.isEditing.set(false);
  }

  generateSpeech(id: number, mode: string) {
    this.sectionsService.generateSpeech(id, mode)
      .subscribe({
        next: () => {
          console.log("Speech generation triggered...");
          // TODO: Response should include IDs of all sections for which speech generation was triggered.
          //  Poll their status.
        }
      })
  }
}
