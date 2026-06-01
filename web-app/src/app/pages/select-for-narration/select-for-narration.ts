import { Component, computed, effect, inject, input, model, viewChild } from '@angular/core';
import { ToolbarComponent } from '../../components/toolbar/toolbar.component';
import { filter, switchMap } from 'rxjs';
import { BooksService } from '../../core/services/books.service';
import { ReadiumService } from '../../core/services/readium.service';
import { ReadiumEpub } from '../../components/readium-epub/readium-epub';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatCheckbox, MatCheckboxChange } from '@angular/material/checkbox';
import { TocItem } from '../../core/models/books.dto';
import { NgClass } from '@angular/common';
import { MatButton } from '@angular/material/button';

@Component({
  selector: 'app-select-for-narration',
  imports: [
    ToolbarComponent,
    ReadiumEpub,
    MatSidenavModule,
    MatCheckbox,
    NgClass,
    MatButton,
  ],
  templateUrl: './select-for-narration.html',
  styleUrl: './select-for-narration.scss',
})
export class SelectForNarration {
  private booksService = inject(BooksService);
  private readiumService = inject(ReadiumService);

  readonly readiumEpub = viewChild(ReadiumEpub);

  bookId = input.required<string>();
  bookDetails = toSignal(toObservable(this.bookId).pipe(
    switchMap(bookId => this.booksService.getBookDetails(bookId))
  ));
  publication = toSignal(toObservable(this.bookDetails).pipe(
    filter(bookDetails => !!bookDetails),
    switchMap(bookDetails => {
      return this.readiumService.getPublication(bookDetails.source_file_key)
    })));

  title = computed(() => this.bookDetails()?.title ?? "Loading...");

  tocItems = model<TocItem[]>();
  currentItem = 0;

  constructor() {
    effect(() => {
      this.booksService.getTableOfContent(this.bookId()).subscribe({
        next: tocItems => {
          this.tocItems.set(tocItems);
        },
      });
    });
  }

  protected navigate(index: number) {
    this.readiumEpub()!.navigate(index);
  }

  protected toggleItem(item: TocItem, index: number, event: MatCheckboxChange) {
    item.narrate = event.checked;
    const allItems = this.tocItems()!;

    // Ensure there is a single sublist of consecutive enabled checkboxes.
    if (event.checked) {
      // Select everything between current item and the first selected behind.
      for (let i = index - 1; i >= 0; i--) {
        if (allItems[i].narrate) {
          for (let j = i + 1; j < index; j++) {
            allItems[j].narrate = true;
          }
          break;
        }
      }

      // Select everything between current item and the first selected ahead.
      for (let i = index + 1; i < allItems.length; i++) {
        if (allItems[i].narrate) {
          for (let j = index + 1; j < i; j++) {
            allItems[j].narrate = true;
          }
          break;
        }
      }
    } else {
      // If this results into two subsets of selected elements, unselect all elements in the smaller subset.

      let selectedBehind = 0;
      for (let i = index - 1; i >= 0; i--) {
        if (allItems[i].narrate) {
          selectedBehind++;
        } else {
          break;
        }
      }

      let selectedAhead = 0;
      for (let i = index + 1; i < allItems.length; i++) {
        if (allItems[i].narrate) {
          selectedAhead++;
        } else {
          break;
        }
      }

      // If there are selected items behind and ahead, then unselect smaller subset.
      if (selectedBehind && selectedAhead) {
        if (selectedBehind <= selectedAhead) {
          // unselect all behind
          for (let i = index - 1; i >= 0; i--) {
            if (allItems[i].narrate) {
              allItems[i].narrate = false;
            } else {
              break;
            }
          }
        } else {
          // unselect all ahead
          for (let i = index + 1; i < allItems.length; i++) {
            if (allItems[i].narrate) {
              allItems[i].narrate = false;
            } else {
              break;
            }
          }
        }
      }
    }
  }
}
