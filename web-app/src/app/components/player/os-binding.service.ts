import { Injectable } from '@angular/core';
import { AudioPlayerService } from './audio-player.service';
import { filter } from 'rxjs';

const SUPPORTED_ACTIONS: MediaSessionAction[] = ["nexttrack", "pause", "play", "previoustrack", "seekbackward", "seekforward", "seekto", "stop"];
type HandlerMap = {
  [key in MediaSessionAction]?: MediaSessionActionHandler;
};

/**
 * Binds OS controls to the player.
 */
@Injectable({providedIn: 'root'})
export class OSBindingsService {

  private actionHandlers: HandlerMap = {
    "pause": (details: MediaSessionActionDetails) => {
      this.audioPlayer.pause();
    },
    "play": (details: MediaSessionActionDetails) => {
      this.audioPlayer.play();
    },
    "seekbackward": (details: MediaSessionActionDetails) => {
      this.audioPlayer.seek(details.seekOffset || -5);
    },
    "seekforward": (details: MediaSessionActionDetails) => {
      this.audioPlayer.seek(details.seekOffset || 5);
    },
    "seekto": (details: MediaSessionActionDetails) => {
      this.audioPlayer.seekTo(details.seekTime);
    },
    "stop": (details: MediaSessionActionDetails) => {
      this.audioPlayer.pause();
    },
  };

  constructor(private audioPlayer: AudioPlayerService) {
    SUPPORTED_ACTIONS.forEach((action) => {
      try {
        const handler = this.actionHandlers[action];
        if (!handler) {
          console.debug("Action %s is not supported yet.", action)
          return;
        }
        const loggingWrapper = (details: MediaSessionActionDetails) => {
          console.debug("Handling %s action from OS", details.action);
          handler(details);
        };
        navigator.mediaSession.setActionHandler(action, loggingWrapper);
      } catch (error) {
        console.error(`The media session action "${action}" is not supported.`);
      }
    });

    this.audioPlayer.$bookDetails
      .pipe(filter(book => book != null))
      .subscribe(
        bookDetails => {
          navigator.mediaSession.metadata = new MediaMetadata({
            title: bookDetails.title
          });
        }
      );

    this.audioPlayer.$playbackPosition.subscribe(
      position => {
        navigator.mediaSession.setPositionState(position);
      }
    );
  }
}
