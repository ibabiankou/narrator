import { AudioPlayer } from './audio.player';
import { filter } from 'rxjs';
import { FilesService } from '../../core/services/files.service';

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
  private artworkUrl: string | null = null;

  constructor(private audioPlayer: AudioPlayer, private filesService: FilesService) {
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

    this.audioPlayer.bookDetails$
      .pipe(
        filter(book => book != null)
      ).subscribe((book) => {
        this.updateMediaSession(book.title ?? "Unknown", book.cover ?? null);
      }
    );
  }

  private updateMediaSession(title: string, artworkUrl: string | null) {
    this.artworkUrl = artworkUrl;

    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: title,
        artwork: artworkUrl ? [{src: artworkUrl}] : [],
      });
    }
  }

  onDestroy(): void {
    SUPPORTED_ACTIONS.forEach((action) => {
      try {
        navigator.mediaSession.setActionHandler(action, null);
      } catch (error) {
        console.error(`The media session action "${action}" is not supported.`);
      }
    });
    if (this.artworkUrl) {
      URL.revokeObjectURL(this.artworkUrl);
    }
  }
}
