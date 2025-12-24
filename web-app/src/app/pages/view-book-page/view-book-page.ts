import {
  AfterViewInit,
  Component,
  computed,
  ElementRef,
  inject,
  input,
  model,
  OnInit, QueryList,
  signal,
  ViewChildren
} from '@angular/core';
import { BookDetails, BookPage, BookStatus, Playlist, Section } from '../../core/models/books.dto';
import { InfiniteScrollDirective } from 'ngx-infinite-scroll';
import { BooksService } from '../../core/services/books.service';
import {
  BehaviorSubject,
  defer,
  filter,
  of,
  repeat,
  switchMap,
  take,
  tap,
  throwError,
  timer
} from 'rxjs';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { MatIcon } from '@angular/material/icon';
import { MatToolbar } from '@angular/material/toolbar';
import { RouterLink } from '@angular/router';
import { SectionComponent } from '../../components/section/section.component';
import { PlayerComponent } from '../../components/player/player.component';
import { AsyncPipe } from '@angular/common';

@Component({
  selector: 'app-view-book-page',
  imports: [
    InfiniteScrollDirective,
    MatProgressSpinner,
    MatIcon,
    MatToolbar,
    RouterLink,
    SectionComponent,
    PlayerComponent,
    AsyncPipe
  ],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage implements OnInit, AfterViewInit {
  private booksService = inject(BooksService);

  book = model.required<BookDetails>();
  pages = model.required<BookPage[]>();
  playlist = input.required<Playlist>();
  sections = computed<Section[]>(() => this.pages().flatMap(page => page.sections))

  isLoading = signal(true);
  isEditingSection = model(false);
  isShowingPages = model(false);

  $scrollToSectionId = new BehaviorSubject<number>(0);

  @ViewChildren("section", {"read": ElementRef}) sectionElements!: QueryList<ElementRef>;

  ngAfterViewInit() {
    this.scrollToSection(this.$scrollToSectionId.value);
    this.sectionElements.changes.subscribe(() => {
      this.scrollToSection(this.$scrollToSectionId.value);
    })
  }

  ngOnInit() {
    const book = this.book();
    const bookIsNotReady = book.status != BookStatus.ready;
    this.isLoading.set(bookIsNotReady);
    if (bookIsNotReady) {
      // Poll book status until it is ready. Use exponential backoff between retries.
      // Once it's ready, fetch the book content.
      this.booksService.getBook(book.id)
        .pipe(
          // Exponential backoff between retries.
          repeat({
            count: 25,
            delay: (count) => timer(2 ^ count * 300 * (0.75 + 0.5 * Math.random()))
          }),
          filter((book) => book.status == BookStatus.ready),
          tap(book => this.book.set(book)),
          take(1),
          switchMap((book) => this.booksService.getBookContent(book.id))
        ).subscribe(
        (content) => {
          this.pages.set(content.pages);
          this.isLoading.set(false);
        }
      );
    }
    const sectionId = this.playlist().progress.section_id;
    if (sectionId != null) {
      this.$scrollToSectionId.next(sectionId);
    }
  }

  scrollToSection(sectionId: number) {
    const selector = `section-${sectionId}`;
    const element = this.sectionElements.find(e => e.nativeElement.id == selector);
    if (element) {
      element.nativeElement.scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
      this.loadSectionIfMissing(sectionId);
    }
  }

  loadSectionIfMissing(sectionId: number) {
    if (sectionId == 0) {
      this.$scrollToSectionId.next(0);
      return;
    }
    const bookId = this.book().id;
    const pages = this.pages();
    const section = pages.flatMap(page => page.sections).find(s => s.id == sectionId);
    const $loadSection =
      this.booksService.getBookContent(bookId, pages[pages.length - 1].index, sectionId)
        .pipe(
          tap(content => {
            this.pages.set([...pages, ...content.pages])
          }),
          switchMap(content => {
            const section = content.pages.flatMap(page => page.sections).find(s => s.id == sectionId);
            if (section) {
              return of(section);
            } else {
              return throwError(() => new Error("Section is not loaded"));
            }
          })
        );
    defer(() => section ? of(section) : $loadSection)
      .subscribe({
        error: err => {
          console.log(err)
        }
      });
  }

  loadMorePages() {
    const bookId = this.book().id;
    const pages = this.pages()

    this.booksService.getBookContent(bookId, pages[pages.length - 1].index).subscribe(
      content => {
        this.pages.set([...pages, ...content.pages]);
      }
    );
  }

  deleteSection(section: Section) {
    const pages = this.pages();
    const page = pages[section.page_index]
    page.sections = page.sections.filter(s => s.id != section.id);
  }

  protected setEditingSection(isEditing: boolean) {
    this.isEditingSection.set(isEditing);
  }

  protected showOrHidePages(showPages: boolean) {
    this.isShowingPages.set(showPages);
  }
}
