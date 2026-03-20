import { Component, computed, inject, input, signal, TemplateRef, viewChild, WritableSignal } from '@angular/core';
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
import { Router, RouterLink } from '@angular/router';
import { OwnerDirective } from '../../../core/ownerDirective';
import { toObservable } from '@angular/core/rxjs-interop';
import { filter, interval, Subscription, switchMap, take } from 'rxjs';
import { BookOverview, BookStats, DownloadInfo } from '../../../core/models/books.dto';
import { DownloadService } from '../../../core/services/download.service';

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
    MatDialogTitle,
    OwnerDirective,
    RouterLink
  ],
  templateUrl: './book-menu.html',
  styleUrl: './book-menu.scss',
})
export class BookMenu {
  private booksService: BooksService = inject(BooksService);
  private settingsService: SettingsService = inject(SettingsService);
  private downloadService: DownloadService = inject(DownloadService);
  private dialog = inject(MatDialog);
  private router: Router = inject(Router);

  private downloadSubscription: Subscription | null = null;

  bookOverview = input.required<BookOverview>();
  bookStats = input.required<BookStats>();
  showPages = computed(() => <string>this.settingsService.userPreferences()!["viewer_mode"]);

  downloadInfo: WritableSignal<DownloadInfo | undefined> = signal(undefined);
  isDownloaded = computed(() => this.downloadInfo() != undefined);
  isDownloading = computed(() => {
    const info = this.downloadInfo();
    if (!info) {
      return false;
    }
    return !(info.fragments_total > 0 && info.fragments_downloaded == info.fragments_total);
  });

  readonly storageInfoTemplate = viewChild.required('storageInfoTemplate', {read: TemplateRef});

  constructor() {
    // Continue download if it's not completed.
    this.downloadSubscription = toObservable(this.downloadInfo)
      .pipe(
        take(1),
        filter(info => !!info),
        filter(info => info && (info.fragments_total == 0 || info.fragments_total > info.fragments_downloaded)),
        switchMap(() => this.downloadService.downloadBook(this.bookOverview().id)),
      )
      .subscribe({
        complete: () => {
          this.downloadSubscription = null;
          this.reloadDownloadInfo();
        }
      });
  }

  setShowPages(viewerMode: string) {
    this.settingsService.patchUserPreferences({viewer_mode: viewerMode});
  }

  protected downloadBookDialog(templateRef: TemplateRef<any>) {
    const dialogRef = this.dialog.open(templateRef);

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.downloadSubscription = this.downloadService.downloadBook(this.bookOverview().id).subscribe();
        this.reloadDownloadInfo();
        this.storageInfoDialog(this.storageInfoTemplate());
      }
    });
  }

  protected storageInfoDialog(templateRef: TemplateRef<any>) {
    const dialogRef = this.dialog.open(templateRef);

    const reloadInterval = interval(500).subscribe(() => this.reloadDownloadInfo());
    dialogRef.afterClosed().subscribe(result => {
      reloadInterval.unsubscribe();
      if (result) {
        if (this.downloadSubscription) {
          this.downloadSubscription.unsubscribe();
          this.downloadSubscription = null;
        }
        this.downloadService.deleteBookData(this.bookOverview().id);
        this.reloadDownloadInfo();
      }
    });
  }

  private formatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  });

  protected totalSizeMb() {
    return this.formatter.format(this.bookStats().total_size_bytes / 1024 / 1024);
  }

  protected downloadProgressPercent(): string {
    const info = this.downloadInfo();
    if (!info || info.fragments_total == 0) {
      return "0";
    } else {
      return this.formatter.format(info.fragments_downloaded / info.fragments_total * 100);
    }
  }

  private reloadDownloadInfo() {
    this.downloadService.getDownloadInfo(this.bookOverview().id)
      .subscribe(val => this.downloadInfo.set(val));
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
    this.booksService.delete(this.bookOverview().id).subscribe(
      () => {
        this.router.navigate(['/books']);
      }
    );
  }
}
