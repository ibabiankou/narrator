import { Component, ContentChild, Directive } from '@angular/core';
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
  @ContentChild(BreadcrumbContentDirective) breadcrumbContent?: BreadcrumbContentDirective;
  @ContentChild(ActionButtonContentDirective) actionButtonContent?: ActionButtonContentDirective;

  get hasBreadcrumbContent(): boolean {
    return !!this.breadcrumbContent;
  }
}
