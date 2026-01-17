import {
  AfterViewInit,
  Component,
  computed,
  ElementRef,
  inject,
  input,
  model,
  QueryList,
  ViewChildren
} from '@angular/core';
import { BookStatus, Section } from '../../core/models/books.dto';
import { BooksService } from '../../core/services/books.service';
import {
  BehaviorSubject,
  filter,
  repeat,
  switchMap,
  take,
  tap,
  timer
} from 'rxjs';
import { MatIcon } from '@angular/material/icon';
import { MatToolbar } from '@angular/material/toolbar';
import { RouterLink } from '@angular/router';
import { SectionComponent } from '../../components/section/section.component';
import { PlayerComponent } from '../../components/player/player.component';
import { AsyncPipe } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

@Component({
  selector: 'app-view-book-page',
  imports: [
    MatIcon,
    MatToolbar,
    RouterLink,
    SectionComponent,
    PlayerComponent,
    AsyncPipe,
    SkeletonComponent
  ],
  templateUrl: './view-book-page.html',
  styleUrl: './view-book-page.scss',
})
export class ViewBookPage implements AfterViewInit {
  private booksService = inject(BooksService);
  private titleService = inject(Title);

  bookId = input.required<string>();

  private _bookWithContent = toSignal(
    toObservable(this.bookId).pipe(
      switchMap(id =>
        this.booksService.getBookWithContent(id)
          .pipe(
            repeat({
              count: 25,
              delay: (count) => timer(2 ^ count * 300 * (0.75 + 0.5 * Math.random()))
            }),
            filter((book) => book.overview.status == BookStatus.ready),
            take(1),
          )
      ),
      tap(book => this.titleService.setTitle(`${book.overview.title} - NNarrator`)),
    ))
  bookWithContent = computed(() => this._bookWithContent()!);

  pages = computed(() => this.bookWithContent().pages);
  sections = computed<Section[]>(() => this.pages().flatMap(page => page.sections))

  isEditingSection = model(false);
  isShowingPages = model(false);

  $currentSectionId = new BehaviorSubject<number>(0);

  @ViewChildren("section", {"read": ElementRef}) sectionElements!: QueryList<ElementRef>;

  ngAfterViewInit() {
    this.scrollToSection(this.$currentSectionId.value);
    this.sectionElements.changes.subscribe(() => {
      this.scrollToSection(this.$currentSectionId.value);
    })
  }

  scrollToSection(sectionId: number) {
    if (sectionId == 0) return;
    const selector = `section-${sectionId}`;
    const element = this.sectionElements.find(e => e.nativeElement.id == selector);
    if (element) {
      element.nativeElement.scrollIntoView({behavior: "smooth", block: "center"});
    } else {
      console.warn("Section that is being played is not found. Section id:", sectionId);
    }
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

  protected setCurrentSectionId(sectionId: number) {
    this.$currentSectionId.next(sectionId);
    this.scrollToSection(sectionId);
  }
}
