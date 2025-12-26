import { Component, HostListener, input, model, OnDestroy, OnInit, output } from '@angular/core';
import { AudioTrack, BookStatus, PlaybackProgress, Playlist } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import {
  BehaviorSubject,
  combineLatest, combineLatestWith, defer,
  filter,
  interval,
  map, of, repeat,
  Subject,
  Subscription,
  switchMap,
  take,
  takeUntil, takeWhile,
  tap, timer,
} from 'rxjs';
import { AsyncPipe, DecimalPipe } from '@angular/common';
import { PlaylistsService } from '../../core/services/playlists.service';
import { ActivatedRoute } from '@angular/router';
import { AudioPlayerService } from './audio-player.service';
import { MatTooltip } from '@angular/material/tooltip';

@Component({
  selector: 'app-player',
  imports: [
    MatIcon,
    MatIconButton,
    AsyncPipe,
    DecimalPipe,
    MatTooltip
  ],
  templateUrl: './player.component.html',
  styleUrl: './player.component.scss',
})
export class PlayerComponent implements OnInit, OnDestroy {
  private $destroy = new Subject<boolean>();

  playlist = input.required<Playlist>();
  sectionPlayed = output<number>();
  showPages = model(false);
  showPagesChanged = output<boolean>();
  syncCurrentSection = model(true);

  handleKeyBindings = input(true);

  // Total duration of the narrated part.
  private readonly $totalNarratedSeconds = new BehaviorSubject<number>(0)

  $isPlaying;
  $nowTime;
  $remainingTime;
  $nowPercent;
  $playbackRate;

  $availablePercent = new BehaviorSubject<number>(0);
  $queuedPercent = new BehaviorSubject<number>(0);
  $unavailablePercent = new BehaviorSubject<number>(0);


  private writerSubscription: Subscription;

  constructor(private playlistService: PlaylistsService,
              private activeRoute: ActivatedRoute,
              private audioPlayer: AudioPlayerService) {
    this.$isPlaying = this.audioPlayer.$isPlaying;
    this.$playbackRate = this.audioPlayer.$playbackRate;
    this.$nowTime = this.audioPlayer.$globalProgressSeconds.pipe(
      map(progressSeconds => secondsToTimeFormat(progressSeconds))
    );
    this.$remainingTime = combineLatest([this.audioPlayer.$globalProgressSeconds, this.$totalNarratedSeconds])
      .pipe(map(([nowTime, totalTime]) => secondsToTimeFormat(nowTime - totalTime)));
    this.$nowPercent = combineLatest([this.audioPlayer.$globalProgressSeconds, this.$totalNarratedSeconds, this.$availablePercent])
      .pipe(
        map(([nowTime, totalTime, availablePercent]) =>
          totalTime > 0 ? (nowTime / totalTime * availablePercent) : 0
        )
      );

    this.audioPlayer.$audioTrack
      .pipe(filter(() => this.syncCurrentSection()))
      .subscribe(track => this.sectionPlayed.emit(track.section_id));

    this.writerSubscription = interval(5000)
      .pipe(
        combineLatestWith(this.audioPlayer.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
        takeUntil(this.$destroy),
      ).subscribe(() => this.updateProgress());

    const bookId = this.activeRoute.snapshot.paramMap.get("id")!;
    let isGenerating = false;
    this.audioPlayer.$trackIndex
      .pipe(
        takeUntil(this.$destroy),
        filter(trackIndex => this.audioPlayer.getNumberOfTracks() > 0 && trackIndex >= this.audioPlayer.getNumberOfTracks() - 5),
        filter(() => !isGenerating),
        tap(() => isGenerating = true),
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
          isGenerating = false;
        }
      });
    });
  }

  private updateProgress() {
    combineLatest([this.audioPlayer.$trackProgress, this.audioPlayer.$playbackRate])
      .pipe(
        take(1),
        switchMap(([{track, progressSeconds}, playbackRate]) => {
          return this.playlistService.updateProgress({
            "book_id": track.book_id,
            "section_id": track.section_id,
            "section_progress_seconds": progressSeconds,
            "sync_current_section": this.syncCurrentSection(),
            "playback_rate": playbackRate
          });
        })
    ).subscribe();
  }

  ngOnInit(): void {
    this.setPlaylist(this.playlist());
  }

  setPlaylist(playlist: Playlist) {
    this.audioPlayer.addTracks(playlist.tracks);
    this.syncCurrentSection.set(playlist.progress.sync_current_section);
    this.audioPlayer.setPlaybackRate(playlist.progress.playback_rate);

    let trackIndex = 0;
    if (playlist.progress.section_id) {
      trackIndex = playlist.tracks.findIndex(t => t.section_id == playlist.progress.section_id);
    }
    const trackProgress = playlist.progress.section_progress_seconds || 0;
    this.audioPlayer.playTrack(trackIndex, trackProgress);

    this.setAvailability(playlist.progress);
  }

  setAvailability(progress: PlaybackProgress) {
    this.$totalNarratedSeconds.next(progress.total_narrated_seconds);

    this.$availablePercent.next(progress.available_percent);
    this.$queuedPercent.next(progress.queued_percent);
    this.$unavailablePercent.next(progress.unavailable_percent);
  }

  @HostListener("document:keydown.shift.arrowleft", ["$event"])
  previous(e: Event) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.audioPlayer.previous();
  }

  @HostListener("document:keydown.arrowleft", ["$event"])
  replay(e: Event) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.audioPlayer.seek(-5);
  }

  @HostListener("window:keydown.space", ["$event"])
  playPause(e: Event) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();

    this.audioPlayer.$isPlaying
      .pipe(take(1)).subscribe((isPlaying) => {
      if (isPlaying) {
        this.audioPlayer.pause();
      } else {
        this.audioPlayer.play();
      }
    });
  }

  @HostListener("document:keydown.arrowright", ["$event"])
  forward(e: Event) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.audioPlayer.seek(5);
  }

  @HostListener("document:keydown.shift.arrowright", ["$event"])
  next(e: Event) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.audioPlayer.next();
  }

  @HostListener("document:keydown.shift.arrowup", ["$event"])
  increasePlaybackRate(e: Event) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.audioPlayer.adjustPlaybackRate(0.05);
  }

  @HostListener("document:keydown.shift.arrowdown", ["$event"])
  lowerPlaybackRate(e: Event) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.audioPlayer.adjustPlaybackRate(-0.05);
  }

  ngOnDestroy(): void {
    this.audioPlayer.destroy();
    this.$destroy.next(true);
    this.$destroy.complete();
    this.writerSubscription.unsubscribe();
  }

  toggleSync() {
    this.syncCurrentSection.set(!this.syncCurrentSection());
    if (!this.syncCurrentSection()) {
      this.sectionPlayed.emit(0);
    } else {
      this.audioPlayer.$audioTrack.pipe(take(1))
        .subscribe(track => this.sectionPlayed.emit(track.section_id));
    }
  }

  toggleShowPages() {
    this.showPages.set(!this.showPages());
    this.showPagesChanged.emit(this.showPages());
  }
  showPagesTooltip() {
    return this.showPages() ? "Hide PDF pages" : "Show PDF pages";
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
