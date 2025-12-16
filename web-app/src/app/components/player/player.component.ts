import { Component, HostListener, input, model, OnDestroy, OnInit, output } from '@angular/core';
import { AudioTrack, BookStatus, PlaybackProgress, Playlist } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { environment } from '../../../environments/environment';
import {
  BehaviorSubject,
  combineLatest, combineLatestWith, defer, distinct,
  filter, from,
  interval,
  map, of, repeat,
  Subject,
  Subscription,
  switchMap,
  take,
  takeUntil, takeWhile,
  tap, throwError, timer, zip,
} from 'rxjs';
import { AsyncPipe } from '@angular/common';
import { PlaylistsService } from '../../core/services/playlists.service';
import { ActivatedRoute } from '@angular/router';

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
  sectionPlayed = output<number>();
  emitSectionId = model(true);

  playerState: PlayerState;

  constructor(private playlistService: PlaylistsService,
              private activeRoute: ActivatedRoute) {
    this.playerState = new PlayerState(this.playlistService, this.activeRoute);
    this.playerState.audioPlayer.$audioTrack
      .pipe(filter(() => this.emitSectionId()))
      .subscribe(track => this.sectionPlayed.emit(track.section_id));
  }

  ngOnInit(): void {
    this.playerState.setPlaylist(this.playlist());
  }

  @HostListener("document:keydown.shift.arrowleft", ["$event"])
  previous(e: Event) {
    e.preventDefault();
    this.playerState.audioPlayer.previous();
  }

  @HostListener("document:keydown.arrowleft", ["$event"])
  replay(e: Event) {
    e.preventDefault();
    this.playerState.audioPlayer.seek(-5);
  }

  @HostListener("window:keydown.space", ["$event"])
  playpause(e: Event) {
    e.preventDefault();
    this.playerState.playPause();
  }

  @HostListener("document:keydown.arrowright", ["$event"])
  forward(e: Event) {
    e.preventDefault();
    this.playerState.audioPlayer.seek(5);
  }

  @HostListener("document:keydown.shift.arrowright", ["$event"])
  next(e: Event) {
    e.preventDefault();
    this.playerState.audioPlayer.next();
  }

  ngOnDestroy(): void {
    this.playerState.destroy();
  }

  toggleSync() {
    this.emitSectionId.set(!this.emitSectionId());
    if (!this.emitSectionId()) {
      this.sectionPlayed.emit(0);
    } else {
      this.playerState.audioPlayer.$audioTrack.pipe(take(1))
        .subscribe(track => this.sectionPlayed.emit(track.section_id));
    }
  }
}

// A single place for all logic around managing the state of the player.
class PlayerState {
  audioPlayer: AudioPlayer = new AudioPlayer();

  $destroy = new Subject<boolean>();
  // Interval that writes progress to the server.
  writerSubscription: Subscription;

  // Total duration of the narrated part.
  private readonly $totalNarratedSeconds = new BehaviorSubject<number>(0)

  $nowTime = this.audioPlayer.$globalProgressSeconds.pipe(
    map(progressSeconds => secondsToTimeFormat(progressSeconds))
  );
  $remainingTime = combineLatest([this.audioPlayer.$globalProgressSeconds, this.$totalNarratedSeconds])
    .pipe(map(([nowTime, totalTime]) => secondsToTimeFormat(nowTime - totalTime)));

  $availablePercent = new BehaviorSubject<number>(0);
  $queuedPercent = new BehaviorSubject<number>(0);
  $unavailablePercent = new BehaviorSubject<number>(0);

  $nowPercent = combineLatest([this.audioPlayer.$globalProgressSeconds, this.$totalNarratedSeconds, this.$availablePercent])
    .pipe(
      map(([nowTime, totalTime, availablePercent]) =>
        totalTime > 0 ? (nowTime / totalTime * availablePercent) : 0
      )
    );

  private isGenerating = false;

  constructor(private playlistService: PlaylistsService, private activeRoute: ActivatedRoute) {
    this.writerSubscription = interval(5000)
      .pipe(
        combineLatestWith(this.audioPlayer.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
        takeUntil(this.$destroy),
      ).subscribe(() => this.updateProgress());

    // Trigger generation of the next sections when reaching the end of available tracks.
    const bookId = this.activeRoute.snapshot.paramMap.get("id")!;
    this.audioPlayer.$trackIndex
      .pipe(
        takeUntil(this.$destroy),
        filter(trackIndex => this.audioPlayer.getNumberOfTracks() > 0 && trackIndex >= this.audioPlayer.getNumberOfTracks() - 5),
        filter(() => !this.isGenerating),
        tap(() => this.isGenerating = true),
        switchMap(() => this.playlistService.generateTracks(bookId))
      ).subscribe((playlist) => {
      let sectionIds = playlist.tracks.map(t => t.section_id);
      defer(() => of(sectionIds))
        .pipe(
          repeat({delay: () => timer(5_000 * (0.75 + 0.5 * Math.random()))}),
          takeWhile((sections) => sections.length > 0),
          switchMap(sectionIds => this.playlistService.getTracks(bookId, sectionIds))
        ).subscribe((tracks) => {
        const readyTracks: AudioTrack[] = [];
        const incompleteSectionIds: number[] = [];
        let skipReady = false;
        for (let i = 0; i < tracks.tracks.length; i++) {
          if (!skipReady && tracks.tracks[i].status != BookStatus.ready) {
            skipReady = true;
          }
          if (skipReady) {
            incompleteSectionIds.push(tracks.tracks[i].section_id);
          } else {
            readyTracks.push(tracks.tracks[i]);
          }
        }
        this.audioPlayer.addTracks(readyTracks);
        sectionIds = incompleteSectionIds;

        this.setAvailability(tracks.progress);
        if (sectionIds.length == 0) {
          this.isGenerating = false;
        }
      });
    });
  }

  setPlaylist(playlist: Playlist) {
    this.audioPlayer.addTracks(playlist.tracks);

    let trackIndex = 0;
    if (playlist.progress.section_id) {
      trackIndex = playlist.tracks.findIndex(t => t.section_id == playlist.progress.section_id);
    }
    const trackProgress = playlist.progress.section_progress_seconds || 0;
    this.audioPlayer.setProgress(trackIndex, trackProgress);

    this.setAvailability(playlist.progress);
  }

  setAvailability(progress: PlaybackProgress) {
    this.$totalNarratedSeconds.next(progress.total_narrated_seconds);

    this.$availablePercent.next(progress.available_percent);
    this.$queuedPercent.next(progress.queued_percent);
    this.$unavailablePercent.next(progress.unavailable_percent);
  }

  private updateProgress() {
    this.audioPlayer.$trackProgress.pipe(
      take(1),
      switchMap(({track, progressSeconds}) => {
        return this.playlistService.updateProgress({
          "book_id": track.book_id,
          "section_id": track.section_id,
          "section_progress_seconds": progressSeconds,
        });
      })
      ).subscribe();
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
  audioBuffer?: AudioBuffer;
}

enum PlayerStatus {
  stopped = "stopped",
  playing = "playing",
  paused = "paused",
}

/**
 * Responsible for playback logic: Playing each track, navigating back and forth, changing tracks.
 */
class AudioPlayer {
  private $status = new BehaviorSubject<PlayerStatus>(PlayerStatus.stopped);
  private $audioContext = new BehaviorSubject<AudioContext | null>(null);

  private tracks: PlayerTrack[] = [];
  // Holds global book time at which each track starts.
  private durationSum: number[] = [0];

  private $destroy = new Subject<boolean>();

  readerSubscription: Subscription;

  $trackIndex = new BehaviorSubject<number>(0);
  private $trackOffset = new BehaviorSubject<number>(0);
  private $currentContextTime = new BehaviorSubject<number>(0);
  private $currentTrackProgressSeconds = combineLatest([this.$trackOffset, this.$currentContextTime])
    .pipe(map(([offset, currentTime]) => offset + currentTime));

  $isPlaying = this.$status.pipe(map((status) => status == PlayerStatus.playing));

  $audioTrack = combineLatest([this.$trackIndex, this.$isPlaying])
    .pipe(
      filter(([_, isPlaying]) => isPlaying),
      map(([trackIndex, _]) => this.tracks[trackIndex]?.audioTrack),
      filter(track => track != null),
      distinct()
    );

  $trackProgress = combineLatest([this.$trackIndex, this.$currentTrackProgressSeconds])
    .pipe(
      map(([trackIndex, progress]) => ({
        track: this.tracks[trackIndex]?.audioTrack,
        progressSeconds: progress,
      }))
    );

  // Progress from the start of the book.
  $globalProgressSeconds = combineLatest([this.$trackIndex, this.$currentTrackProgressSeconds])
    .pipe(map(([index, progress]) => this.durationSum[index] + progress));

  constructor() {
    zip([this.$trackIndex, this.$trackOffset])
      .pipe(
        takeUntil(this.$destroy),
        filter(([trackIndex, _]) => trackIndex >= 0 && trackIndex < this.tracks.length),
        switchMap(
          ([trackIndex, trackOffset]) => {
            return this.$status.pipe(
              take(1),
              filter(status => status == PlayerStatus.playing),
              switchMap(() => {
                this.$audioContext.pipe(take(1)).subscribe(ac => ac?.close());

                const track = this.tracks[trackIndex];
                if (track == null) {
                  return throwError(() => new Error("Invalid track index"));
                }

                let audioContext = new AudioContext();
                this.$audioContext.next(audioContext);

                let audioBuffer;
                if (track.audioBuffer != null) {
                  audioBuffer = of(track.audioBuffer);
                } else if (track.url) {
                  audioBuffer = from(fetch(track.url)).pipe(
                    switchMap(response => response.arrayBuffer()),
                    switchMap(arrayBuffer => audioContext.decodeAudioData(arrayBuffer)),
                    tap(audioBuffer => track.audioBuffer = audioBuffer)
                  )
                } else {
                  return throwError(() => new Error("Track without URL"));
                }

                return audioBuffer.pipe(
                  switchMap(audioBuffer => this.connectSource(audioContext, audioBuffer)),
                  tap(source => {
                    source.start(0, trackOffset);
                    source.addEventListener("ended", () => {
                      this.readProgress();
                      if (this.tracks.length > trackIndex + 1) {
                        this.$trackIndex.next(trackIndex + 1);
                        this.$trackOffset.next(0);
                      }
                    });
                  })
                );
              }));
          }
        )
      ).subscribe();

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

  getNumberOfTracks() {
    return this.tracks.length;
  }

  addTracks(tracks: AudioTrack[]) {
    const baseUrl = environment.api_base_url

    const length = tracks.length;
    let newTracks: PlayerTrack[] = tracks.map((track, index) => ({
      audioTrack: track,
      url: `${baseUrl}/books/${track.book_id}/speech/${track.file_name}`,
      index: length + index
    }));

    for (let i = 0; i < tracks.length; i++) {
      this.durationSum.push(this.durationSum[this.durationSum.length - 1] + tracks[i].duration);
    }

    this.tracks.push(...newTracks);
  }

  setProgress(startTrackIndex: number, trackOffsetSeconds: number) {
    this.$trackIndex.next(startTrackIndex);
    this.$trackOffset.next(trackOffsetSeconds);
  }

  play() {
    combineLatest([this.$status, this.$audioContext, this.$trackIndex, this.$trackOffset]).pipe(take(1)).subscribe(
      ([status, audioContext, index, offset]) => {
        this.$status.next(PlayerStatus.playing);
        if (status == PlayerStatus.paused) {
          audioContext?.resume();
        } else if (status == PlayerStatus.stopped) {
          this.$trackIndex.next(index);
          this.$trackOffset.next(offset);
        }
      });
  }

  pause() {
    this.$audioContext.pipe(filter(ac => ac != null), take(1))
      .subscribe(
        (audioContext) => {
          audioContext.suspend();
          this.readProgress();
          this.$status.next(PlayerStatus.paused);
        }
      )
  }

  next() {
    this.$trackIndex.pipe(take(1)).subscribe(
      (current) => {
        const next = current + 1;
        if (next >= this.tracks.length) {
          return;
        }
        this.$trackIndex.next(next);
        this.$trackOffset.next(0);
      });
  }

  previous() {
    this.$trackIndex.pipe(take(1)).subscribe(
      (current) => {
        const prev = current - 1;
        if (prev < 0) {
          return;
        }
        this.$trackIndex.next(prev);
        this.$trackOffset.next(0);
      });
  }

  private connectSource(audioContext: AudioContext, audioBuffer: AudioBuffer) {
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    return of(source);
  }

  getTrack(trackIndex: number) {
    return this.tracks[trackIndex].audioTrack;
  }

  destroy() {
    this.$destroy.next(true);
  }

  seek(adjustment: number) {
    this.readProgress();
    combineLatest([this.$trackIndex, this.$currentTrackProgressSeconds]).pipe(take(1)).subscribe(
      ([trackIndex, trackProgressSeconds]) => {
        let track = this.getTrack(trackIndex);
        let newProgress = trackProgressSeconds + adjustment;

        if (newProgress < 0) {
          if (trackIndex == 0) {
            // Start from the beginning if it's the first track.
            this.$trackIndex.next(0);
            this.$trackOffset.next(0);
            return;
          } else {
            // It's not the first track, so go to the previous track.
            track = this.getTrack(trackIndex - 1);
            newProgress += track.duration;
            this.$trackIndex.next(trackIndex - 1);
            this.$trackOffset.next(newProgress);
            return;
          }
        } else if (newProgress > track.duration) {
          if (trackIndex == this.tracks.length - 1) {
            // It's the last track, so seek the end. It should stop playback.
            this.$trackIndex.next(trackIndex);
            this.$trackOffset.next(track.duration);
            return;
          } else {
            // Go to the next track.
            newProgress -= track.duration;
            this.$trackIndex.next(trackIndex + 1);
            this.$trackOffset.next(newProgress);
            return;
          }
        } else {
          // We are within the current track, so simply change the progress.
          this.$trackIndex.next(trackIndex);
          this.$trackOffset.next(newProgress);
          return;
        }
      });
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
