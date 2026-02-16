import { Component, ElementRef, inject, input, output, Renderer2, signal } from '@angular/core';
import { Section } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { MatInput } from '@angular/material/input';
import { CdkTextareaAutosize } from '@angular/cdk/text-field';
import { SectionsService } from '../../core/services/sections.service';
import { ThemeService } from '../../core/services/theme.service';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { combineLatest } from 'rxjs';

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
  private sectionsService: SectionsService = inject(SectionsService);
  private themeService: ThemeService = inject(ThemeService);

  section = input.required<Section>();
  sectionDeleted = output();
  isEditing = signal(false)
  current = input.required<boolean>();

  editingModeChanged = output<boolean>();

  constructor(private el: ElementRef, private renderer: Renderer2) {
    combineLatest([toObservable(this.current), this.themeService.isDark$])
      .pipe(takeUntilDestroyed())
      .subscribe(([isCurrent, isDark]) => {
        if (isCurrent) {
          this.renderer.setStyle(this.el.nativeElement, 'background-color', isDark ? '#3c3c3c' : '#d3d3d3');
        } else {
          this.renderer.removeStyle(this.el.nativeElement, 'background-color');
        }
      });
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
