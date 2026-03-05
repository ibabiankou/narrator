import { Directive, ElementRef, EventEmitter, Output, OnInit, OnDestroy } from '@angular/core';

@Directive({selector: '[observeVisibility]'})
export class VisibilityDirective implements OnInit, OnDestroy {
  @Output() visible = new EventEmitter<boolean>();
  isVisible: boolean = false;
  private observer?: IntersectionObserver;

  constructor(private el: ElementRef) {
  }

  ngOnInit() {
    this.observer = new IntersectionObserver(([entry]) => {
      this.visible.emit(entry.isIntersecting);
      this.isVisible = entry.isIntersecting;
    }, {threshold: 0.1}); // Triggers when 10% of the element is visible

    this.observer.observe(this.el.nativeElement);
  }

  ngOnDestroy() {
    this.observer?.disconnect();
  }
}
