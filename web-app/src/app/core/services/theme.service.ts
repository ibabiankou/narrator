import { Injectable, Renderer2, RendererFactory2, Inject } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { DOCUMENT } from '@angular/common';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private renderer: Renderer2;
  private isDark = new BehaviorSubject<boolean>(window.matchMedia('(prefers-color-scheme: dark)').matches);
  isDark$ = this.isDark.asObservable();

  constructor(rendererFactory: RendererFactory2, @Inject(DOCUMENT) private document: Document) {
    this.renderer = rendererFactory.createRenderer(null, null);
  }

  setTheme(dark: boolean) {
    console.log("Setting theme to:", dark ? "dark" : "light");
    this.isDark.next(dark);
    if (dark) {
      this.renderer.addClass(this.document.body, 'dark-mode');
      this.renderer.removeClass(this.document.body, 'light-mode');

    } else {
      this.renderer.addClass(this.document.body, 'light-mode');
      this.renderer.removeClass(this.document.body, 'dark-mode');
    }
  }
}
