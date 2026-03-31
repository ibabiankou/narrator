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
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map, tap } from 'rxjs';

@Directive({
  selector: '[breadcrumb]',
  standalone: true
})
export class BreadcrumbContentDirective {
}

@Directive({
  selector: '[center]',
  standalone: true
})
export class CenterContentDirective {
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

  private readonly breakpointObserver = inject(BreakpointObserver);

  @ContentChild(BreadcrumbContentDirective) breadcrumbContent?: BreadcrumbContentDirective;
  @ContentChild(CenterContentDirective) centerContent?: CenterContentDirective;
  @ContentChild(ActionButtonContentDirective) actionButtonContent?: ActionButtonContentDirective;

  settings = toSignal(this.settingsService.userPreferences$);

  isMobile = toSignal(
    this.breakpointObserver
      .observe([Breakpoints.Handset])
      .pipe(map(result => result.matches), tap(result => console.log("isMobile", result))),
    { initialValue: false }
  );

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
