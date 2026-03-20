import { Component, computed, inject, input, TemplateRef } from '@angular/core';
import { MatButtonToggle, MatButtonToggleGroup } from '@angular/material/button-toggle';
import { MatIcon } from '@angular/material/icon';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';
import {
  MatDialog,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogTitle
} from '@angular/material/dialog';
import { SettingsService } from '../../../core/services/settings.service';
import { BooksService } from '../../../core/services/books.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-book-menu',
  imports: [
    MatButtonToggle,
    MatButtonToggleGroup,
    MatIcon,
    MatIconButton,
    MatMenu,
    MatMenuItem,
    MatMenuTrigger,
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle
  ],
  templateUrl: './book-menu.html',
  styleUrl: './book-menu.scss',
})
export class BookMenu {
  private booksService: BooksService = inject(BooksService);
  private settingsService: SettingsService = inject(SettingsService);
  private dialog = inject(MatDialog);
  private router: Router = inject(Router);

  bookId = input.required<string>();
  showPages = computed(() => <string>this.settingsService.userPreferences()!["viewer_mode"]);

  setShowPages(viewerMode: string) {
    this.settingsService.patchUserPreferences({viewer_mode: viewerMode});
  }

  protected deleteBookDialog(templateRef: TemplateRef<any>) {
    const dialogRef = this.dialog.open(templateRef);

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.deleteBook();
      }
    });
  }

  private deleteBook() {
    this.booksService.delete(this.bookId()).subscribe(
      () => {
        this.router.navigate(['/books']);
      }
    );
  }
}
