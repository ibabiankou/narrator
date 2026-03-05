import { Component, inject, model, OnInit } from '@angular/core';
import { MatFabButton, MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { Router, RouterLink } from '@angular/router';
import { BookOverview } from '../../core/models/books.dto';
import { MatToolbar } from '@angular/material/toolbar';
import { Title } from '@angular/platform-browser';
import { toSignal } from '@angular/core/rxjs-interop';
import { BooksService } from '../../core/services/books.service';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import {
  ActionButtonContentDirective,
  BreadcrumbContentDirective,
  ToolbarComponent
} from '../../components/toolbar/toolbar.component';
import { HideIdleDirective } from '../../core/hideIdleDirective';
import { MatButtonToggle, MatButtonToggleGroup } from '@angular/material/button-toggle';
import { MatMenu, MatMenuItem } from '@angular/material/menu';

@Component({
  selector: 'app-books-page',
  imports: [
    MatIcon,
    MatFabButton,
    RouterLink,
    MatToolbar,
    SkeletonComponent,
    ActionButtonContentDirective,
    BreadcrumbContentDirective,
    HideIdleDirective,
    MatButtonToggle,
    MatButtonToggleGroup,
    MatIconButton,
    MatMenu,
    MatMenuItem,
    ToolbarComponent,
  ],
  templateUrl: './books-page.html',
  styleUrl: './books-page.scss',
})
export class BooksPage implements OnInit {
  private titleService = inject(Title);
  private router: Router = inject(Router);
  private bookService = inject(BooksService);

  books = toSignal(this.bookService.listBooks());

  ngOnInit() {
    this.titleService.setTitle('Books - NNarrator');
  }

  navigateToAdd() {
    this.router.navigate(['/add-book']);
  }
}
