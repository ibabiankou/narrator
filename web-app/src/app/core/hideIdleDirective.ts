import { Directive, ElementRef, Input, NgZone, OnDestroy, OnInit, Renderer2 } from '@angular/core';

@Directive({
  selector: '[appHideIdle]'
})
export class HideIdleDirective implements OnInit, OnDestroy {
  @Input() idleTime = 3000;
  @Input() hideClass = 'hidden';

  private timeoutId: any;
  private isHidden = false;
  private removeListeners: (() => void)[] = [];

  constructor(private ngZone: NgZone, private renderer: Renderer2, private el: ElementRef) {}

  ngOnInit() {
    this.ngZone.runOutsideAngular(() => {
      const events = ['mousemove', 'keydown', 'touchstart'];
      events.forEach(event => {
        const unlisten = this.renderer.listen('window', event, () => this.handleActivity());
        this.removeListeners.push(unlisten);
      });
    });
    this.startTimer();
  }

  private handleActivity() {
    if (this.timeoutId) clearTimeout(this.timeoutId);

    if (this.isHidden) {
      this.isHidden = false;
      this.ngZone.run(() => {
        this.renderer.removeClass(this.el.nativeElement, this.hideClass);
      });
    }
    this.startTimer();
  }

  private startTimer() {
    this.timeoutId = setTimeout(() => {
      this.isHidden = true;
      this.ngZone.run(() => {
        this.renderer.addClass(this.el.nativeElement, this.hideClass);
      });
    }, this.idleTime);
  }

  ngOnDestroy() {
    if (this.timeoutId) clearTimeout(this.timeoutId);
    this.removeListeners.forEach(fn => fn());
  }
}
