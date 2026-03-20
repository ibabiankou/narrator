import { Component, ContentChild, Directive, inject } from '@angular/core';
import { MatIcon } from '@angular/material/icon';
import { MatToolbar } from '@angular/material/toolbar';
import { RouterLink } from '@angular/router';
import { MatIconButton } from '@angular/material/button';
import Keycloak from 'keycloak-js';
import { MatButtonToggle, MatButtonToggleGroup } from '@angular/material/button-toggle';
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';
import { toSignal } from '@angular/core/rxjs-interop';
import { SettingsService } from '../../core/services/settings.service';
import { ThemeService } from '../../core/services/theme.service';

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
    MatButtonToggle,
    MatButtonToggleGroup,
    MatMenu,
    MatMenuItem,
    MatMenuTrigger,
  ],
  templateUrl: './toolbar.component.html',
  styleUrl: './toolbar.component.scss',
})
export class ToolbarComponent {
  private readonly keycloak = inject(Keycloak);
  private readonly settingsService = inject(SettingsService);
  private readonly themeService = inject(ThemeService);

  @ContentChild(BreadcrumbContentDirective) breadcrumbContent?: BreadcrumbContentDirective;
  @ContentChild(ActionButtonContentDirective) actionButtonContent?: ActionButtonContentDirective;

  settings = toSignal(this.settingsService.userPreferences$);

  get hasBreadcrumbContent(): boolean {
    return !!this.breadcrumbContent;
  }

  protected setTheme(theme: string) {
    this.themeService.setTheme(theme);
    this.settingsService.patch("user_preferences", {theme: theme}).subscribe();
  }

  logout() {
    this.keycloak.logout();
  }
}
