import { Component, effect, HostListener, input, model, output } from '@angular/core';
import { TocItem } from '../../core/models/books.dto';
import { MatCheckbox } from '@angular/material/checkbox';
import { NgClass } from '@angular/common';
import { MatSidenav, MatSidenavContainer, MatSidenavContent } from '@angular/material/sidenav';


@Component({
  selector: 'app-toc',
  standalone: true,
  imports: [
    MatCheckbox,
    NgClass,
    MatSidenav,
    MatSidenavContainer,
    MatSidenavContent,
  ],
  templateUrl: './toc.component.html',
  styleUrl: './toc.component.scss',
})
export class TocComponent {
  tocItems = input.required<TocItem[]>();
  currentTocItemIndex = input<number>(0);
  allowSelection = input<boolean>(false);

  showToC = model<boolean>(false);

  currentItemChanged = output<number>();

  protected itemClicked(index: number) {
    this.currentItemChanged.emit(index);
  }

  @HostListener("window:keydown.arrowdown", [])
  next() {
    this.itemClicked(this.currentTocItemIndex() + 1);
  }

  @HostListener("window:keydown.arrowup", [])
  prev() {
    this.itemClicked(this.currentTocItemIndex() - 1);
  }

  protected toggleItem(index: number) {
    const allItems = this.tocItems()!;
    const item = allItems[index];
    item.narrate = !item.narrate;

    // Ensure there is a single sublist of consecutive enabled checkboxes.
    if (item.narrate) {
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

  @HostListener("window:keydown.space", [])
  toggle() {
    if (this.allowSelection()) {
      this.toggleItem(this.currentTocItemIndex());
    }
  }
}
