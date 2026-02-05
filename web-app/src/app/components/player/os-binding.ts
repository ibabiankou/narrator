import { AudioPlayer } from './audio.player';
import { filter } from 'rxjs';

const SUPPORTED_ACTIONS: MediaSessionAction[] = ["nexttrack", "pause", "play", "previoustrack", "seekbackward", "seekforward", "seekto", "stop"];
type HandlerMap = {
  [key in MediaSessionAction]?: MediaSessionActionHandler;
};

/**
 * Binds OS controls to the player.
 */
export class OSBindings {

  private actionHandlers: HandlerMap = {
    "nexttrack": (details: MediaSessionActionDetails) => {
      this.audioPlayer.next();
    },
    "pause": (details: MediaSessionActionDetails) => {
      this.audioPlayer.pause();
    },
    "play": (details: MediaSessionActionDetails) => {
      this.audioPlayer.play();
    },
    "previoustrack": (details: MediaSessionActionDetails) => {
      this.audioPlayer.previous();
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

  constructor(private audioPlayer: AudioPlayer) {
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
  }

  onDestroy(): void {
    SUPPORTED_ACTIONS.forEach((action) => {
      try {
        navigator.mediaSession.setActionHandler(action, null);
      } catch (error) {
        console.error(`The media session action "${action}" is not supported.`);
      }
    });
  }
}
