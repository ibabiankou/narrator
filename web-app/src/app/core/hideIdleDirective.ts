import {
  Directive,
  effect,
  ElementRef,
  EventEmitter,
  Input,
  NgZone,
  OnDestroy,
  Output,
  Renderer2
} from '@angular/core';
import { FullScreenService } from './services/fullScreen.service';

@Directive({
  selector: '[appHideIdle]'
})
export class HideIdleDirective implements OnDestroy {
  @Input() idleTime = 3000;
  @Input() hideClass = 'hidden';
  @Output() hidden = new EventEmitter<boolean>();

  private timeoutId: any;
  private isHidden = false;
  private removeListeners: (() => void)[] = [];

  constructor(
    private fullScreenService: FullScreenService,
    private ngZone: NgZone,
    private renderer: Renderer2,
    private el: ElementRef) {

    effect(() => {
      if (this.fullScreenService.fullScreen()) {
        this.ngZone.runOutsideAngular(() => {
          const events = ['mousemove', 'keydown', 'touchstart'];
          events.forEach(event => {
            const unlisten = this.renderer.listen('window', event, () => this.handleActivity());
            this.removeListeners.push(unlisten);
          });
        });
        this.startTimer();
      } else {
        this.handleActivity();
        this.ngOnDestroy();
      }
    });
  }

  private handleActivity() {
    if (this.timeoutId) clearTimeout(this.timeoutId);

    if (this.isHidden) {
      this.isHidden = false;
      this.hidden.emit(this.isHidden);
      this.ngZone.run(() => {
        this.renderer.removeClass(this.el.nativeElement, this.hideClass);
      });
    }
    this.startTimer();
  }

  private startTimer() {
    this.timeoutId = setTimeout(() => {
      this.isHidden = true;
      this.hidden.emit(this.isHidden);
      this.ngZone.run(() => {
        this.renderer.addClass(this.el.nativeElement, this.hideClass);
      });
    }, this.idleTime);
  }

  ngOnDestroy() {
    this.isHidden = false;
    this.hidden.emit(this.isHidden);

    if (this.timeoutId) clearTimeout(this.timeoutId);
    this.removeListeners.forEach(fn => fn());

    while (this.removeListeners.length > 0) {
      this.removeListeners.pop();
    }
  }
}
