import { Component, inject, input, OnDestroy } from '@angular/core';
import { FilesService } from '../../core/services/files.service';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { BehaviorSubject, filter, take } from 'rxjs';
import { AsyncPipe } from '@angular/common';

@Component({
  selector: 'app-book-page',
  templateUrl: './book-page.html',
  styleUrl: './book-page.scss',
  imports: [
    AsyncPipe
  ]
})
export class BookPage implements OnDestroy {
  private fileService: FilesService = inject(FilesService);
  private sanitizer: DomSanitizer = inject(DomSanitizer);

  fileUrl = input.required<string>();
  protected blobData?: SafeResourceUrl;
  protected isVisible = new BehaviorSubject(false);

  private url?: string;

  constructor() {
    this.isVisible
      .pipe(
        filter((isVisible) => isVisible && this.blobData === undefined),
        take(1)
      )
      .subscribe(() => this.getPageData());
  }

  protected getPageData() {
    this.fileService.getFileData(this.fileUrl())
      .pipe(take(1))
      .subscribe(fileData => {
        const buffer = fileData.data as ArrayBuffer;
        const blob = new Blob([buffer], {type: 'application/pdf'});
        this.url = URL.createObjectURL(blob);
        const fullUrl = `${this.url}#toolbar=0&navpanes=0&scrollbar=0`
        this.blobData = this.sanitizer.bypassSecurityTrustResourceUrl(fullUrl);
      });
  }

  setVisibility($event: boolean) {
    this.isVisible.next($event);
  }

  ngOnDestroy(): void {
    if (this.url) {
      URL.revokeObjectURL(this.url);
    }
  }
}
