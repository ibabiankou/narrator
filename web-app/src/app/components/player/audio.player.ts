import { BookOverview, PlaybackInfo } from '../../core/models/books.dto';
import {
  BehaviorSubject,
  combineLatest,
  combineLatestWith,
  distinctUntilChanged,
  filter,
  interval,
  map,
  switchMap,
  take,
  tap,
} from 'rxjs';

import Hls, { AttrList } from 'hls.js';
import { BooksService } from '../../core/services/books.service';
import { CachingHlsLoader } from '../../core/services/cachingHlsLoader';
import { OSBindings } from './os-binding';
import { FilesService } from '../../core/services/files.service';
import { binarySearch } from '../../core/utils';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

enum PlayerStatus {
  playing = "playing",
  paused = "paused",
}

interface FragmentTimelineItem {
  id: string;
  index: number
  startTime: number;
  endTime: number;
  duration: number;
}

/**
 * Responsible for playback logic: Playing each track, navigating back and forth, changing tracks.
 */
export class AudioPlayer {
  private osBindings: OSBindings;

  private status$ = new BehaviorSubject<PlayerStatus>(PlayerStatus.paused);
  private readonly audio: HTMLAudioElement;
  private hls: Hls | null = null;

  bookDetails$ = new BehaviorSubject<BookOverview | null>(null);
  // Currently playing time in seconds.
  globalProgressSeconds$ = new BehaviorSubject<number>(0);
  private timeDrift = -1;

  // Total duration of all tracks in playlist in seconds.
  totalDuration$ = new BehaviorSubject<number>(-1);
  // Total size of all tracks in playlist in bytes.
  totalSize$ = new BehaviorSubject<number>(-1);

  playbackRate$ = new BehaviorSubject<number>(-1);
  isPlaying$ = this.status$.pipe(map((status) => status == PlayerStatus.playing));

  private fragmentTimeline: FragmentTimelineItem[] = [];
  currentFragment$ = new BehaviorSubject<FragmentTimelineItem | null>(null);

  constructor(private bookService: BooksService, filesService: FilesService) {
    this.osBindings = new OSBindings(this, filesService);

    this.audio = new Audio();
    this.audio.preservesPitch = true;
    this.audio.addEventListener('timeupdate', () => this.readProgress());

    this.bookDetails$
      .pipe(filter(book => book != null))
      .subscribe((book) => {
        if (!Hls.isSupported()) {
          console.error("HLS not supported");
          return;
        }

        this.hls = new Hls({
          maxBufferLength: 600,
          loader: CachingHlsLoader,
          debug: false,
        });

        this.hls.on(Hls.Events.LEVEL_UPDATED, (eventName, data) => {
          console.debug("Handling: %s", eventName, data);

          if (data.details.fragments) {
            let cumulativeSize = 0;
            let cumulativeDuration = 0;
            let fragments: FragmentTimelineItem[] = [];

            data.details.fragments.forEach(fragment => {
              fragment.tagList.forEach(tag => {
                const tagName = tag[0];
                const attributes = tag[1];

                if (tagName == "EXT-X-DATERANGE") {
                  const attr = AttrList.parseAttrList(attributes);
                  if (attr["X-DURATION"]) {
                    const durationNum = parseFloat(attr["X-DURATION"]);
                    const frag = {
                      id: attr["ID"],
                      index: fragments.length,
                      startTime: cumulativeDuration,
                      endTime: cumulativeDuration + durationNum,
                      duration: durationNum,
                    };
                    fragments.push(frag);
                    cumulativeDuration = frag.endTime;
                  }
                  if (attr["X-SIZE"]) {
                    cumulativeSize += parseInt(attr["X-SIZE"]);
                  }
                }
              });
            });

            this.totalSize$.next(cumulativeSize)
            this.totalDuration$.next(cumulativeDuration);
            this.fragmentTimeline = fragments;
          }

          if (!this.fragmentTimeline) {
            console.warn("No date ranges found, unable to sync fragment being played.")
          }
        });

        // Update time drift each time a new audio track is started.
        this.hls.on(Hls.Events.FRAG_CHANGED, (eventName, data) => {
          console.debug("Handling: %s", eventName, data);

          if (data.frag) {
            if (this.timeDrift < 0) {
              // Skip the first fragment change because of the assumption that most of the time
              // the first fragment is not started from the beginning of the audio track.
              this.timeDrift = 0;
            } else {
              this.timeDrift = this.audio.currentTime - data.frag.playlistOffset;
              console.debug("Time drift: ", this.timeDrift);
            }
          } else {
            console.warn("Frag changed event data is missing.")
          }
        });

        // Pause once end is reached.
        this.hls.on(Hls.Events.MEDIA_ENDED, () => {
          this.pause();
        });

        const masterPlaylistUrl = `/api/files/${book?.id}/playlists/master.m3u8`;
        this.hls.loadSource(masterPlaylistUrl);
        this.hls.attachMedia(this.audio);

        this.audio.playbackRate = this.playbackRate$.value;

        // Boost the volume
        const audioContext = new window.AudioContext();
        const source = audioContext.createMediaElementSource(this.audio);
        const gainNode = audioContext.createGain();
        source.connect(gainNode);
        gainNode.connect(audioContext.destination);
        gainNode.gain.value = 2.5;
      });

    this.playbackRate$.subscribe(() => {
      if (this.audio && this.playbackRate$.value > 0) {
        this.audio.playbackRate = this.playbackRate$.value;
      }
    });

    this.globalProgressSeconds$.pipe(
      map((currentTime) => {
        const currentFragment = this.currentFragment$.value;
        if (currentFragment) {
          // Check current and next
          if (currentTime >= currentFragment.startTime) {
            if (currentTime < currentFragment.endTime) {
              // It's still current fragment...
              return currentFragment;
            } else if (currentFragment.index + 1 < this.fragmentTimeline.length) {
              // check the next fragment, assuming we are simply listening and went to the next one.
              const nextFragment = this.fragmentTimeline[currentFragment.index + 1];
              if (currentTime >= nextFragment.startTime && currentTime <= nextFragment.endTime) {
                return nextFragment;
              }
            }
          }
        }

        const fragmentIndex = binarySearch(this.fragmentTimeline, (i) => i.startTime, currentTime);
        if (fragmentIndex >= 0) {
          const fragment = this.fragmentTimeline[fragmentIndex];
          if (currentTime >= fragment.startTime && currentTime < fragment.endTime) {
            return fragment;
          }
        }

        console.warn("Unable to find fragment for current time: ", currentTime);
        return null;
      }),
      distinctUntilChanged(),
      tap((fragment) => {
        this.currentFragment$.next(fragment);
      }),
      takeUntilDestroyed()
    ).subscribe();

    interval(5000)
      .pipe(
        combineLatestWith(this.isPlaying$),
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

    this.status$.complete();
    this.bookDetails$.complete();
    this.globalProgressSeconds$.complete();
    this.playbackRate$.complete();
  }

  private readProgress() {
    this.globalProgressSeconds$.next(this.getCurrentTime());
  }

  private updateProgress() {
    combineLatest([this.bookDetails$.pipe(filter(b => b != null)), this.globalProgressSeconds$])
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
      this.status$.next(PlayerStatus.playing);
    }
  }

  pause() {
    if (this.audio) {
      this.audio.pause();
      this.readProgress();
      this.updateProgress();
      this.status$.next(PlayerStatus.paused);
    }
  }

  next() {
    // TODO: Should it go to the next ToC item?
  }

  previous() {
    // TODO: Should it go to the previous ToC item?
  }

  seek(adjustment: number) {
    // Since the change is relative to the current time, don't bother with time drift.
    this.timeDrift = -1;
    this.audio.currentTime += adjustment;
  }

  seekTo(seekTime: number | undefined) {
    if (seekTime == undefined) {
      return;
    }
    this.timeDrift = -1;
    this.setCurrentTime(seekTime);
  }

  setPlaybackRate(playbackRate: number) {
    this.playbackRate$.next(playbackRate);
  }

  adjustPlaybackRate(adjustment: number) {
    const maxValue = 2;
    const minValue = 0.75;
    const newRate = Math.max(Math.min(this.playbackRate$.value + adjustment, maxValue), minValue);
    this.setPlaybackRate(newRate);
  }

  initPlayer(overview: BookOverview, playbackInfo: PlaybackInfo) {
    this.bookDetails$.next(overview);
    if (playbackInfo.data["progress_seconds"]) {
      this.setCurrentTime(playbackInfo.data["progress_seconds"]);
    }
  }

  getDurationSeconds(): number {
    return this.audio.duration;
  }
}
