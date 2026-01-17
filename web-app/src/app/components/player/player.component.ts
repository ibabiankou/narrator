import { Component, HostListener, input, model, OnDestroy, OnInit, output } from '@angular/core';
import { BookDetails, PlaybackProgress, Playlist } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import {
  BehaviorSubject,
  combineLatest,
  filter,
  map,
  Subject,
  take,
  takeUntil,
} from 'rxjs';
import { AsyncPipe, DecimalPipe } from '@angular/common';
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

  book = input.required<BookDetails>();
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
  $unavailablePercent = new BehaviorSubject<number>(0);

  constructor(private audioPlayer: AudioPlayerService) {

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

    this.audioPlayer.$sectionId
      .pipe(
        filter(() => this.syncCurrentSection()),
        takeUntil(this.$destroy)
      ).subscribe(sectionId => this.sectionPlayed.emit(sectionId));
  }

  ngOnInit(): void {
    this.initPlayerService(this.playlist(), this.book());
    this.setAvailability(this.playlist().progress);
  }

  initPlayerService(playlist: Playlist, book: BookDetails) {
    this.audioPlayer.setBookDetails(book);
    this.audioPlayer.setPlaybackProgress(playlist.progress);
  }

  setAvailability(progress: PlaybackProgress) {
    this.$totalNarratedSeconds.next(progress.total_narrated_seconds);

    this.$availablePercent.next(progress.available_percent);
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
  increasePlaybackRate(e: Event, adjustment: number = 0.1) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.audioPlayer.adjustPlaybackRate(adjustment);
  }

  @HostListener("document:keydown.shift.arrowdown", ["$event"])
  lowerPlaybackRate(e: Event, adjustment: number = -0.1) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.audioPlayer.adjustPlaybackRate(adjustment);
  }

  private clickTimer: number = -1;

  protected clickPlaybackRate(e: PointerEvent) {
    if (this.clickTimer > 0) {
      // This is a consequent click, so do nothing.
      return;
    }

    this.clickTimer = setTimeout(() => {
      if (e.shiftKey) {
        this.lowerPlaybackRate(e);
      } else {
        this.increasePlaybackRate(e);
      }
      this.clickTimer = -1;
    }, 250);
  }

  protected dblclickPlaybackRate(e: MouseEvent) {
    clearTimeout(this.clickTimer);
    this.clickTimer = -1;
    this.lowerPlaybackRate(e);
  }

  ngOnDestroy(): void {
    this.$destroy.next(true);
    this.$destroy.complete();
  }

  toggleSync() {
    this.syncCurrentSection.set(!this.syncCurrentSection());
    if (!this.syncCurrentSection()) {
      this.sectionPlayed.emit(0);
    } else {
      this.audioPlayer.$sectionId.pipe(take(1))
        .subscribe(sectionId => this.sectionPlayed.emit(sectionId));
    }
  }

  toggleShowPages() {
    this.showPages.set(!this.showPages());
    this.showPagesChanged.emit(this.showPages());
  }

  showPagesTooltip() {
    return this.showPages() ? "Hide PDF pages" : "Show PDF pages";
  }

  private fontSizeIndex = 1;
  private fontSizeOptions = ["90%", "100%", "110%"];

  protected toggleFontSize(_: PointerEvent) {
    this.fontSizeIndex = (this.fontSizeIndex + 1) % this.fontSizeOptions.length;
    document.documentElement.style.setProperty('--font-scale', this.fontSizeOptions[this.fontSizeIndex]);
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
