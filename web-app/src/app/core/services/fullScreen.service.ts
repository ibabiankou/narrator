import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class FullScreenService {
  fullScreen = signal<boolean>(false);

  constructor() {
    document.addEventListener('fullscreenchange', () => {
      this.fullScreen.set(!!document.fullscreenElement);
    })
  }

  toggleFullScreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
        .catch((err: any) => {
          console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
    } else {
      document.exitFullscreen();
    }
  }
}
