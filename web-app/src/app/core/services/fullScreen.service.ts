import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class FullScreenService {
  fullScreen = signal<boolean>(false);

  toggleFullScreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
        .then(() => {
          this.fullScreen.set(true);
        })
        .catch((err: any) => {
          console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
    } else {
      document.exitFullscreen().then(() => {
        this.fullScreen.set(false);
      });
    }
  }
}
