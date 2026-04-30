import { Directive, Input, TemplateRef, ViewContainerRef, OnDestroy, OnInit } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Directive({
  selector: '[appRenderIf]',
  standalone: true
})
export class RenderIfDirective implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  private hasView = false;
  private renderInMode: 'mobile' | 'desktop' = 'desktop';

  @Input() set appRenderIf(mode: 'mobile' | 'desktop') {
    this.renderInMode = mode;
  }

  constructor(
    private breakpointObserver: BreakpointObserver,
    private templateRef: TemplateRef<any>,
    private viewContainer: ViewContainerRef
  ) {}

  ngOnInit() {
    const mobileQueries = [
      Breakpoints.HandsetPortrait,
      Breakpoints.HandsetLandscape
    ];

    this.breakpointObserver
      .observe(mobileQueries)
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        // result.matches will be true if the device is in EITHER mobile orientation
        const isMobile = result.matches;
        const shouldRender =
          (this.renderInMode === 'mobile' && isMobile) ||
          (this.renderInMode === 'desktop' && !isMobile);

        this.updateView(shouldRender);
      });
  }

  private updateView(shouldRender: boolean) {
    if (shouldRender && !this.hasView) {
      this.viewContainer.createEmbeddedView(this.templateRef);
      this.hasView = true;
    } else if (!shouldRender && this.hasView) {
      this.viewContainer.clear();
      this.hasView = false;
    }
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
