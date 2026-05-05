import { Component, computed, HostListener, inject, OnInit } from '@angular/core';
import { MatFabButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { ActivatedRoute, Params, Router, RouterLink } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { BooksService } from '../../core/services/books.service';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import { ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { MatFormField, MatInput } from '@angular/material/input';
import { combineLatest, switchMap } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { FileAsBlobPipe } from '../../core/fileAsBlobPipe';
import { AsyncPipe } from '@angular/common';
import { DEFAULT_PAGE_INFO, DEFAULT_PAGE_SIZE } from '../../core/models/pagination.dto';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { NotificationService } from '../../core/services/notificationService';
import { BookOverview, BookStatus } from '../../core/models/books.dto';

@Component({
  selector: 'app-books-page',
  imports: [
    MatIcon,
    MatFabButton,
    RouterLink,
    SkeletonComponent,
    ToolbarComponent,
    MatFormField,
    MatInput,
    FormsModule,
    FileAsBlobPipe,
    AsyncPipe,
    MatPaginator,
  ],
  templateUrl: './books-page.html',
  styleUrl: './books-page.scss',
})
export class BooksPage implements OnInit {
  private titleService = inject(Title);
  private router: Router = inject(Router);
  private route = inject(ActivatedRoute);
  private bookService = inject(BooksService);
  private notificationService = inject(NotificationService);

  readonly queryParams = toSignal(this.route.queryParams, {initialValue: {} as Params});
  readonly searchQuery = computed(() => String(this.queryParams()['q'] || ''));
  readonly pageIndex = computed(() => Number(this.queryParams()['page_index'] || 0));
  readonly size = computed(() => Number(this.queryParams()['size'] || DEFAULT_PAGE_SIZE));

  private $books =
    combineLatest([toObservable(this.searchQuery), toObservable(this.pageIndex), toObservable(this.size)]).pipe(
      switchMap(([searchQuery, pageIndex, size]) => {
        if (searchQuery != undefined && searchQuery.trim().length > 0) {
          return this.bookService.searchBooks(searchQuery, pageIndex, size);
        } else {
          return this.bookService.listBooks(pageIndex, size);
        }
      })
    );
  private booksPage = toSignal(this.$books);
  readonly books = computed(() => this.booksPage()?.items || []);
  readonly pageInfo = computed(() => this.booksPage()?.page_info || DEFAULT_PAGE_INFO);

  ngOnInit() {
    this.titleService.setTitle('Books - NNarrator');
  }

  protected search(value: any) {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {q: value},
      queryParamsHandling: 'merge',
    });
  }

  protected changePage(pageEvent: PageEvent) {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {page_index: pageEvent.pageIndex, size: pageEvent.pageSize},
      queryParamsHandling: 'merge',
    });
  }

  @HostListener("document:keydown.arrowright", ["$event"])
  nextPage(e: Event) {
    e.preventDefault();
    this.changePage({
      pageIndex: Math.min(Math.floor(this.pageInfo().total / this.pageInfo().size), this.pageInfo().index + 1),
      pageSize: this.pageInfo().size,
      length: this.pageInfo().total,
    })
  }

  @HostListener("document:keydown.arrowleft", ["$event"])
  previousPage(e: Event) {
    e.preventDefault();
    this.changePage({
      pageIndex: Math.max(0, this.pageInfo().index - 1),
      pageSize: this.pageInfo().size,
      length: this.pageInfo().total,
    })
  }

  protected async openFilePicker() {
    const pickerOptions = {
      startIn: "downloads",
      types: [
        {
          description: "PDF Documents",
          accept: {
            "application/pdf": [".pdf"],
          },
        },
      ],
      excludeAcceptAllOption: true,
      multiple: false,
    };
    const [fileHandle]: FileSystemFileHandle[] = await (window as any).showOpenFilePicker(pickerOptions);
    const file = await fileHandle.getFile();
    this.uploadBook(file);
  }

  private uploadBook(file: File) {
    if (file.size > 15 * 1024 * 1024) {
      this.notificationService.showError("Selected file is too large. Maximum size is 15MB.");
      return;
    }
    this.notificationService.showMessage(`Uploading '${file.name}'...`);

    return this.bookService.uploadBook(file)
      .subscribe({
        next: bookDetails => {
          this.notificationService.showMessage(
            "Processing the book. It might take a few seconds. Be patient...",
            10_000);
          this.router.navigate(['/books', bookDetails.id, 'edit-details']);
        },
        error: err => {
          // TODO: show the error message.
          console.error("Error: ", err);
        }
      });
  }

  @HostListener('document:dragover', ['$event'])
  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
  }

  @HostListener('document:drop', ['$event'])
  onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      if (files.length > 1) {
        this.notificationService.showError("Only one book can be added at a time.");
        return;
      }

      // Validate it's a PDF file
      const file = files[0];
      if (file.type !== "application/pdf") {
        this.notificationService.showError("Invalid file type. Only PDF files are supported.");
        return;
      }

      this.uploadBook(file);
    }
  }

  protected bookLink(book: BookOverview) {
    switch (book.status) {
      case BookStatus.ready_for_metadata_review:
        return ['/books', book.id, 'edit-details'];
      case BookStatus.ready_for_content_review:
        return ['/books', book.id, 'edit'];
    }
    return ['/books', book.id];
  }
}
