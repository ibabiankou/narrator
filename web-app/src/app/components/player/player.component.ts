import { Component, input, OnDestroy, OnInit } from '@angular/core';
import { AudioTrack, Playlist } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { environment } from '../../../environments/environment';
import { BooksService } from '../../core/services/books.service';
import {
  BehaviorSubject,
  combineLatest, combineLatestWith,
  filter, from,
  interval,
  map, of,
  Subject,
  Subscription,
  switchMap,
  take,
  takeUntil,
  tap, throwError,
} from 'rxjs';
import { AsyncPipe } from '@angular/common';

@Component({
  selector: 'app-player',
  imports: [
    MatIcon,
    MatIconButton,
    AsyncPipe
  ],
  templateUrl: './player.component.html',
  styleUrl: './player.component.scss',
})
export class PlayerComponent implements OnInit, OnDestroy {
  playlist = input.required<Playlist>();

  playerState: PlayerState;

  constructor(private bookService: BooksService) {
    this.playerState = new PlayerState(this.bookService);
  }

  ngOnInit(): void {
    this.playerState.setPlaylist(this.playlist());
  }

  ngOnDestroy(): void {
    this.playerState?.destroy();
  }

  // TODO: Auto-scroll to the currently played item. I should probably simply emmit event what is being played
  //  (upon start and periodically)
  //  and let the page do the scrolling.
}

// A single place for all logic around managing the state of the player.
class PlayerState {
  audioPlayer: AudioPlayer = new AudioPlayer();

  $destroy = new Subject<boolean>();
  // Interval that writes progress to the server.
  // writerSubscription: Subscription;

  // Holds global book time at which each track starts.
  durationSum: number[] = [];

  // Progress from the start of the book.
  private readonly $progressSeconds = combineLatest([this.audioPlayer.$trackIndex, this.audioPlayer.$currentTrackProgressSeconds])
    .pipe(map(([index, progress]) => this.durationSum[index] + progress));

  // Total duration of the narrated part.
  private readonly $totalNarratedSeconds = new BehaviorSubject<number>(0)

  $nowTime = this.$progressSeconds.pipe(
    map(progressSeconds => secondsToTimeFormat(progressSeconds))
  );
  $remainingTime = combineLatest([this.$progressSeconds, this.$totalNarratedSeconds])
    .pipe(map(([nowTime, totalTime]) => secondsToTimeFormat(nowTime - totalTime)));

  $availablePercent = new BehaviorSubject<number>(0);
  $queuedPercent = new BehaviorSubject<number>(0);
  $unavailablePercent = new BehaviorSubject<number>(0);

  $nowPercent = combineLatest([this.$progressSeconds, this.$totalNarratedSeconds, this.$availablePercent])
    .pipe(
      map(([nowTime, totalTime, availablePercent]) =>
        totalTime > 0 ? (nowTime / totalTime * availablePercent) : 0
      )
    );

  constructor(private bookService: BooksService) {
    // this.writerSubscription = interval(5000)
    //   .pipe(
    //     filter(() => Amplitude.getPlayerState() == "playing"),
    //     takeUntil(this.$destroy),
    //   ).subscribe(() => this.updateProgress());
  }

  setPlaylist(playlist: Playlist) {
    this.durationSum = [0];
    for (let i = 0; i < playlist.tracks.length; i++) {
      this.durationSum.push(this.durationSum[i] + playlist.tracks[i].duration);
    }

    let trackIndex = 0;
    if (playlist.progress.section_id) {
      trackIndex = playlist.tracks.findIndex(t => t.section_id == playlist.progress.section_id);
    }
    const trackProgress = playlist.progress.section_progress_seconds || 0;
    this.audioPlayer.setTracks(playlist.tracks, trackIndex, trackProgress);

    this.$totalNarratedSeconds.next(playlist.progress.total_narrated_seconds);

    this.$availablePercent.next(playlist.progress.available_percent);
    this.$queuedPercent.next(playlist.progress.queued_percent);
    this.$unavailablePercent.next(playlist.progress.unavailable_percent);
  }

  private updateProgress() {
    combineLatest([this.audioPlayer.$trackIndex, this.audioPlayer.$currentTrackProgressSeconds])
      .pipe(
        take(1),
        switchMap(([trackIndex, progressSeconds]) => {
          const track = this.audioPlayer.getTrack(trackIndex);
          return this.bookService.updateProgress({
            "book_id": track.book_id,
            "section_id": track.section_id,
            "section_progress_seconds": progressSeconds,
          });
        })
      )
      .subscribe();
  }

  playPause() {
    this.audioPlayer.$isPlaying
      .pipe(take(1)).subscribe((isPlaying) => {
      if (isPlaying) {
        this.audioPlayer.pause();
      } else {
        this.audioPlayer.play();
      }
    });
  }

  destroy() {
    this.audioPlayer.destroy();
    this.$destroy.next(true);
    this.$destroy.complete();
  }
}

interface PlayerTrack {
  audioTrack: AudioTrack

  url?: string;
  index: number;

  arrayBuffer?: ArrayBuffer;
  // Caching decoded audio might end up taking a lot of memory.
  // audioBuffer?: AudioBuffer;
}

/**
 * Responsible for playback logic: Playing each track, navigating back and forth, changing tracks.
 */
class AudioPlayer {
  private $audioContext = new BehaviorSubject<AudioContext | null>(null);
  private tracks: PlayerTrack[] = [];

  $destroy = new Subject<boolean>();

  // Interval that reads info from Amplitude.
  readerSubscription: Subscription;

  private $currentTrackSourceNode = new BehaviorSubject<AudioBufferSourceNode | null>(null);

  $trackIndex = new BehaviorSubject<number>(0);
  $trackOffset = new BehaviorSubject<number>(0);
  $contextTimeOnStart = new BehaviorSubject<number>(0);
  $currentContextTime = new BehaviorSubject<number>(0);
  $currentTrackProgressSeconds = combineLatest([this.$trackOffset, this.$contextTimeOnStart, this.$currentContextTime])
    .pipe(map(([offset, timeOnStart, currentTime]) => offset + currentTime - timeOnStart));

  // Whether the audioContext is paused.
  $isPaused = new BehaviorSubject<boolean>(false);

  $isPlaying = combineLatest([this.$currentTrackSourceNode, this.$isPaused])
    .pipe(map(([sourceNode, isPaused]) => sourceNode != null && !isPaused));

  constructor() {
    this.readerSubscription = interval(1000)
      .pipe(
        combineLatestWith(this.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
        takeUntil(this.$destroy),
      ).subscribe(() => this.readProgress());
  }

  private readProgress() {
    this.$audioContext
      .pipe(filter(ac => ac != null), take(1))
      .subscribe((audioContext) => {
        this.$currentContextTime.next(audioContext.currentTime);
      });
  }

  setTracks(tracks: AudioTrack[], startTrackIndex: number = 0, trackOffsetSeconds: number = 0) {
    this.stop();
    const baseUrl = environment.api_base_url

    this.tracks = tracks.map((track, index) => ({
      audioTrack: track,
      url: `${baseUrl}/books/${track.book_id}/speech/${track.file_name}`,
      index: index
    }));
    this.$trackIndex.next(startTrackIndex);
    this.$trackOffset.next(trackOffsetSeconds);
  }

  play() {
    combineLatest([this.$trackIndex, this.$trackOffset, this.$audioContext])
      .pipe(take(1))
      .subscribe(([trackIndex, trackOffset, audioContext]) => {
        if (audioContext == null) {
          this.playTrack(trackIndex, trackOffset)
            .subscribe(source => {
              source.addEventListener("ended", (ev) => {
                this.$trackIndex.pipe(take(1))
                  .subscribe(trackIndex => {
                    // TODO: this approach does not work... Need to subscribe. So refactor this to an actual subscription.
                    this.playTrack(trackIndex + 1, 0);
                  });
              });
            });
        } else {
          audioContext.resume();
          this.$isPaused.next(false);
        }
      });
  }

  pause() {
    this.$audioContext.pipe(filter(ac => ac != null), take(1))
      .subscribe(
        (audioContext) => {
          audioContext.suspend();
          this.$isPaused.next(true);
        }
      )
  }

  stop() {
    this.$currentTrackSourceNode.pipe(take(1)).subscribe(
      (source) => {
        if (source) {
          source.stop();
          this.$currentTrackSourceNode.next(null);
        }
      }
    );
  }

  private playAudio(audioContext: AudioContext, audioBuffer: AudioBuffer, offset_seconds: number = 0) {
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start(0, offset_seconds); // Start with 0 second delay
    return of(source);
  }

  private playTrack(trackIndex: number, offsetSeconds: number) {
    console.log("Play track", trackIndex, "offset", offsetSeconds);

    if (trackIndex < 0 || trackIndex >= this.tracks.length) {
      return throwError(() => new Error("Invalid track index"));
    }
    const track = this.tracks[trackIndex];

    if (track.url == null) {
      return throwError(() => new Error("Track URL is null"));
    }

    this.$trackIndex.next(trackIndex);
    this.$trackOffset.next(offsetSeconds);

    let arrayBuffer;
    if (track.arrayBuffer != null) {
      arrayBuffer = of(track.arrayBuffer);
    } else {
      arrayBuffer = from(fetch(track.url)).pipe(
        switchMap(response => response.arrayBuffer()),
        tap(arrayBuffer => track.arrayBuffer = arrayBuffer)
      )
    }

    return this.$audioContext.pipe(
      take(1),
      switchMap(context => {
        let audioContext = context;
        if (audioContext == null) {
          audioContext = new AudioContext();
          this.$audioContext.next(audioContext);
        }

        return arrayBuffer.pipe(
          switchMap(arrayBuffer => audioContext.decodeAudioData(arrayBuffer)),
          switchMap(audioBuffer => this.playAudio(audioContext, audioBuffer, offsetSeconds)),
          tap(source => {
            source.addEventListener("ended", () => {
              this.$currentTrackSourceNode.next(null);
              this.readProgress();
            });
            this.$currentTrackSourceNode.next(source);
          })
        );
      })
    );
  }

  getTrack(trackIndex: number) {
    return this.tracks[trackIndex].audioTrack;
  }

  destroy() {
    this.$destroy.next(true);
  }
}

/**
 * Converts a number of seconds into a time string in (hh:)mm:ss format.
 * If the duration is 1 hour or more, it includes hours (hh:mm:ss).
 * Otherwise, it shows only minutes and seconds (mm:ss).
 *
 * @param totalSeconds The total duration in seconds.
 * @returns The time string in (hh:)mm:ss format.
 */
function secondsToTimeFormat(totalSeconds: number): string {
  const sign = totalSeconds >= 0 ? '' : '-';
  const absSeconds = Math.abs(totalSeconds);

  // 1. Calculate the components
  const seconds = Math.floor(absSeconds % 60);
  const minutes = Math.floor((absSeconds / 60) % 60);
  const hours = Math.floor(absSeconds / 3600);

  // 2. Pad the minutes and seconds with a leading zero if they are less than 10
  const ss = seconds.toString().padStart(2, '0');
  const mm = minutes.toString().padStart(2, '0');

  // 3. Conditional formatting for hours
  if (hours > 0) {
    // Pad hours and include them in the format: hh:mm:ss
    const hh = hours.toString();
    return `${sign}${hh}:${mm}:${ss}`;
  } else {
    // Format as mm:ss
    return `${sign}${mm}:${ss}`;
  }
}
