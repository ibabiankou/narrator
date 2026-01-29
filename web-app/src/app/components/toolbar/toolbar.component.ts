import { Component, ContentChild, Directive, HostListener } from '@angular/core';
import { MatIcon } from '@angular/material/icon';
import { MatToolbar } from '@angular/material/toolbar';
import { RouterLink } from '@angular/router';
import { MatIconButton } from '@angular/material/button';

@Directive({
  selector: '[breadcrumb]',
  standalone: true
})
export class BreadcrumbContentDirective {
}

@Directive({
  selector: '[actionButton]',
  standalone: true
})
export class ActionButtonContentDirective {
}

@Component({
  selector: 'app-toolbar',
  standalone: true,
  imports: [
    MatIcon,
    MatToolbar,
    RouterLink,
    MatIconButton,
  ],
  templateUrl: './toolbar.component.html',
  styleUrl: './toolbar.component.scss',
})
export class ToolbarComponent {

  isMenuVisible = true;
  private lastScrollPosition = 0;

  @ContentChild(BreadcrumbContentDirective) breadcrumbContent?: BreadcrumbContentDirective;
  @ContentChild(ActionButtonContentDirective) actionButtonContent?: ActionButtonContentDirective;

  get hasBreadcrumbContent(): boolean {
    return !!this.breadcrumbContent;
  }

  @HostListener('window:scroll', [])
  onWindowScroll() {
    const currentScroll = window.pageYOffset || document.documentElement.scrollTop;

    if (currentScroll <= 10) {
      this.isMenuVisible = true;
    } else if (currentScroll > this.lastScrollPosition) {
      // Scrolling Down
      this.isMenuVisible = false;
    } else {
      // Scrolling Up
      this.isMenuVisible = true;
    }
    this.lastScrollPosition = currentScroll;
  }
}
