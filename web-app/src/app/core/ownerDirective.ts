import { Directive, Input, TemplateRef, ViewContainerRef } from '@angular/core';
import { AuthService } from './services/authService';

@Directive({ selector: '[appOwner]', standalone: true })
export class OwnerDirective {
  private hasView = false;

  @Input() set appOwner(ownerId: string) {
    const isOwner = this.auth.isOwner(ownerId);

    if (isOwner && !this.hasView) {
      this.viewContainer.createEmbeddedView(this.templateRef);
      this.hasView = true;
    } else if (!isOwner && this.hasView) {
      this.viewContainer.clear();
      this.hasView = false;
    }
  }

  constructor(
    private templateRef: TemplateRef<any>,
    private viewContainer: ViewContainerRef,
    private auth: AuthService
  ) {}
}
