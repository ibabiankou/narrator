import { Component, computed, ElementRef, HostListener, inject, input, output, Renderer2, signal } from '@angular/core';
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
  paragraphs = computed(() => this.section().content.split('\n'));
  sectionDeleted = output();
  editable = input<boolean>(false);
  isEditing = signal(false)
  current = input.required<boolean>();

  editingModeChanged = output<boolean>();

  constructor(private el: ElementRef, private renderer: Renderer2) {
    combineLatest([toObservable(this.current), this.themeService.isDark$])
      .pipe(takeUntilDestroyed())
      .subscribe(([isCurrent, isDark]) => {
        this.renderer.removeClass(this.el.nativeElement, 'current-dark');
        this.renderer.removeClass(this.el.nativeElement, 'current-light');

        if (isCurrent) {
          this.renderer.addClass(this.el.nativeElement, isDark ? 'current-dark' : 'current-light');
        }
      });
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

  @HostListener("keydown.shift.enter", ["$event"])
  saveChanges(e: Event) {
    if (!this.isEditing()) {
      return;
    }
    e.preventDefault();

    const textarea = e.target as HTMLTextAreaElement;
    this.saveSection(textarea.value);
  }

  @HostListener("document:keydown.esc", ["$event"])
  cancelOnEscape(e: Event) {
    if (!this.isEditing()) {
      return;
    }
    e.preventDefault();
    this.cancelEditing();
  }
}
