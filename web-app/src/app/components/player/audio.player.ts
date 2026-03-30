import { BookOverview, PlaybackInfo } from '../../core/models/books.dto';
import { BehaviorSubject, combineLatest, combineLatestWith, filter, interval, map, switchMap, take, } from 'rxjs';

import Hls from 'hls.js';
import { BooksService } from '../../core/services/books.service';
import { CachingHlsLoader } from '../../core/services/cachingHlsLoader';
import { OSBindings } from './os-binding';

enum PlayerStatus {
  playing = "playing",
  paused = "paused",
}

interface HlsSection {
  section_id: number;
  duration: number;
  end_time: number;
  playback_order: number;
}

const FIRST_SECTION: HlsSection = {
  section_id: 0,
  duration: 0,
  end_time: 0,
  playback_order: -1
}

/**
 * Responsible for playback logic: Playing each track, navigating back and forth, changing tracks.
 */
export class AudioPlayer {
  private osBindings: OSBindings;

  private $status = new BehaviorSubject<PlayerStatus>(PlayerStatus.paused);
  private readonly audio: HTMLAudioElement;
  private hls: Hls | null = null;

  $bookDetails = new BehaviorSubject<BookOverview | null>(null);
  // A list of sections from the HLS playlist along with their duration and end time.
  private sectionTimeline: HlsSection[] = [];
  // Currently playing time in seconds.
  $globalProgressSeconds = new BehaviorSubject<number>(0);
  private timeDrift = -1;
  // An index within sectionTimeline of the currently playing section.
  private $sectionIndex = new BehaviorSubject<number>(0);
  // An ID of the section that is being played right now.
  $sectionId = this.$sectionIndex.pipe(
    filter(i => i > 0),
    map(i => this.sectionTimeline[i].section_id),
  );

  $playbackRate = new BehaviorSubject<number>(-1);
  $isPlaying = this.$status.pipe(map((status) => status == PlayerStatus.playing));

  constructor(private bookService: BooksService) {
    this.osBindings = new OSBindings(this);

    this.audio = new Audio();
    this.audio.preservesPitch = true;
    this.audio.addEventListener('timeupdate', () => this.readProgress());

    this.$bookDetails
      .pipe(filter(book => book != null))
      .subscribe((book) => {
        if (!Hls.isSupported()) {
          console.error("HLS not supported");
          return;
        }

        this.hls = new Hls({
          loader: CachingHlsLoader,
          debug: false,
        });

        // Get section timeline metadata from HLS model.
        this.hls.on(Hls.Events.LEVEL_UPDATED, (event, data) => {
          if (data.details.dateRanges) {
            const hlsSections: HlsSection[] = [FIRST_SECTION];

            Object.values(data.details.dateRanges).forEach(range => {
              if (!range) return;
              hlsSections.push({
                section_id: parseInt(range.id),
                duration: parseFloat(range.attr["X-DURATION"]),
                end_time: 0,
                playback_order: parseInt(range.attr["X-ORDER"])
              })
            });

            // Ensure the sections are sorted according to the playback order and calculate the cumulative end times.
            hlsSections.sort((a, b) => a.playback_order - b.playback_order);
            hlsSections.forEach((hlsSection, index) => {
              if (index == 0) return;
              hlsSection.end_time = hlsSections[index - 1].end_time + hlsSection.duration;
            });
            this.sectionTimeline = hlsSections;
          } else {
            console.warn("No date ranges found, unable to sync section being played.")
          }
        });

        // Update time drift each time a new audio track is started.
        this.hls.on(Hls.Events.FRAG_CHANGED, (_, data) => {
          if (data.frag) {
            if (this.timeDrift < 0) {
              // Skip the first fragment change because of the assumption that most of the time
              // the first fragment is not started from the beginning of the audio track.
              this.timeDrift = 0;
            } else {
              this.timeDrift = this.audio.currentTime - data.frag.playlistOffset;
            }

            if (typeof data.frag.sn === "number") {
              this.$sectionIndex.next(data.frag.sn + 1);
            }
          } else {
            console.warn("Frag changed event data is missing.")
          }
        });

        this.hls.loadSource(this.bookService.getPlaylistUrl(book?.id));
        this.hls.attachMedia(this.audio);

        this.audio.playbackRate = this.$playbackRate.value;

        // Boost the volume
        const audioContext = new window.AudioContext();
        const source = audioContext.createMediaElementSource(this.audio);
        const gainNode = audioContext.createGain();
        source.connect(gainNode);
        gainNode.connect(audioContext.destination);
        gainNode.gain.value = 2.5;
      });

    this.$playbackRate.subscribe(() => {
      if (this.audio && this.$playbackRate.value > 0) {
        this.audio.playbackRate = this.$playbackRate.value;
      }
    });

    interval(5000)
      .pipe(
        combineLatestWith(this.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
      ).subscribe(() => this.updateProgress());
  }

  onDestroy(): void {
    this.pause();
    if (this.hls) {
      this.hls.destroy();
    }

    if (this.audio) {
      this.audio.removeEventListener('timeupdate', () => this.readProgress());
      this.audio.src = "";
    }

    this.osBindings.onDestroy();

    this.$status.complete();
    this.$bookDetails.complete();
    this.$globalProgressSeconds.complete();
    this.$playbackRate.complete();
  }

  private readProgress() {
    this.$globalProgressSeconds.next(this.getCurrentTime());
  }

  private updateProgress() {
    combineLatest([this.$bookDetails.pipe(filter(b => b != null)), this.$globalProgressSeconds])
      .pipe(
        take(1),
        switchMap(([bookDetails, progressSeconds]) => {
          return this.bookService.updatePlaybackInfo({
            "book_id": bookDetails.id,
            "data": {
              "progress_seconds": progressSeconds
            }
          });
        })
      ).subscribe();
  }

  private getCurrentTime() {
    return this.audio.currentTime - (this.timeDrift > 0 ? this.timeDrift : 0);
  }

  private setCurrentTime(time: number) {
    this.audio.currentTime = time + (this.timeDrift > 0 ? this.timeDrift : 0);
  }

  play() {
    if (this.audio) {
      this.audio.play();
      this.$status.next(PlayerStatus.playing);
    }
  }

  pause() {
    if (this.audio) {
      this.audio.pause();
      this.readProgress();
      this.updateProgress();
      this.$status.next(PlayerStatus.paused);
    }
  }

  next() {
    this.$sectionIndex.pipe(take(1))
      .subscribe(i => {
        // Scrolling to the end time of the current section, effectively starting the next one.
        this.setCurrentTime(this.sectionTimeline[i].end_time);
      });
  }

  previous() {
    this.$sectionIndex.pipe(take(1))
      .subscribe(i => {
        // The end time of the previous section is the start time of the current section, so
        // to play the previous section, we need to go two items back.
        // Add a few extra ms, otherwise it activates the one before previous section for a moment.
        this.setCurrentTime(this.sectionTimeline[Math.max(i - 2, 0)].end_time + 0.05)
      });
  }

  seek(adjustment: number) {
    // Since the change is relative to the current time, don't bother with time drift.
    this.audio.currentTime += adjustment;
  }

  seekTo(seekTime: number | undefined) {
    if (seekTime == undefined) {
      return;
    }
    this.setCurrentTime(seekTime);
    this.timeDrift = -1;
  }

  setPlaybackRate(playbackRate: number) {
    this.$playbackRate.next(playbackRate);
  }

  adjustPlaybackRate(adjustment: number) {
    const maxValue = 2;
    const minValue = 0.5;
    const newRate = Math.max(Math.min(this.$playbackRate.value + adjustment, maxValue), minValue);
    this.setPlaybackRate(newRate);
  }

  initPlayer(overview: BookOverview, playbackInfo: PlaybackInfo) {
    this.$bookDetails.next(overview);
    if (playbackInfo.data["progress_seconds"]) {
      this.setCurrentTime(playbackInfo.data["progress_seconds"]);
    }
  }

  getDurationSeconds(): number {
    return this.audio.duration;
  }
}
