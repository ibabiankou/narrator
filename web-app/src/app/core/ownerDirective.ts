import { computed, Directive, effect, inject, input, TemplateRef, ViewContainerRef } from '@angular/core';
import { AuthService } from './services/authService';

@Directive({ selector: '[appOwnerOrHasRole]', standalone: true })
export class OwnerDirective {
  private auth = inject(AuthService);
  private templateRef = inject(TemplateRef);
  private viewContainer = inject(ViewContainerRef);

  ownerId = input.required<string>({ alias: 'appOwnerOrHasRole' });
  roles = input<string[]>(['admin'], { alias: 'appOwnerOrHasRoleRoles' });

  private hasAccess = computed(() => {
    const isOwner = this.auth.isOwner(this.ownerId());
    const hasRole = this.auth.hasAnyRole(this.roles());
    return isOwner || hasRole;
  });

  constructor() {
    effect(() => {
      this.viewContainer.clear();
      if (this.hasAccess()) {
        this.viewContainer.createEmbeddedView(this.templateRef);
      }
    });
  }
}
