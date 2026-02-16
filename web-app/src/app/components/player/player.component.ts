import { Component, HostListener, inject, input, model, OnDestroy, output, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { BookWithContent, PlaybackInfo } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import {
  BehaviorSubject,
  catchError,
  combineLatest,
  filter,
  map,
  of,
  Subject,
  switchMap,
  take,
  takeUntil,
  throwError,
} from 'rxjs';
import { AsyncPipe, DecimalPipe } from '@angular/common';
import { AudioPlayer } from './audio.player';
import { MatTooltip } from '@angular/material/tooltip';
import { toObservable } from '@angular/core/rxjs-interop';
import { BooksService } from '../../core/services/books.service';

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
export class PlayerComponent implements OnDestroy, AfterViewInit {
  @ViewChild('slider', { static: true }) slider!: ElementRef<HTMLDivElement>;

  private $destroy = new Subject<boolean>();

  private bookService = inject(BooksService);
  private audioPlayer: AudioPlayer;

  bookWithContent = input.required<BookWithContent>();
  private readonly $playbackInfo = toObservable(this.bookWithContent).pipe(
    switchMap(book => this.bookService.getPlaybackInfo(book.overview.id)),
    switchMap(info => {
      return info ? of(info) : throwError(() => new Error("Undefined playback info"))
    }),
    catchError(error => {
      console.warn("Failed to load playback info, falling back to default values.", error);
      return of(<PlaybackInfo>{book_id: this.bookWithContent().overview.id, data: {}});
    })
  )

  sectionPlayed = output<number>();
  showPages = model(false);
  showPagesChanged = output<boolean>();
  syncCurrentSection = model(true);

  handleKeyBindings = input(true);

  // Total duration of the narrated part.
  private readonly $totalNarratedSeconds =
    toObservable(this.bookWithContent).pipe(map(b => b.stats.total_narrated_seconds));

  $isPlaying;
  $nowTime;
  $remainingTime;
  $nowPercent;
  $playbackRate;

  $availablePercent = toObservable(this.bookWithContent).pipe(map(b => b.stats.available_percent));
  $unavailablePercent = this.$availablePercent.pipe(map(availablePercent => 100 - availablePercent));

  $dragToPercent = new BehaviorSubject<number | undefined>(undefined);
  private sliderRect!: DOMRect;

  constructor() {
    this.audioPlayer = new AudioPlayer(this.bookService);

    this.$isPlaying = this.audioPlayer.$isPlaying;
    this.$playbackRate = this.audioPlayer.$playbackRate;

    const dragTimeSeconds = combineLatest([this.$dragToPercent, this.$totalNarratedSeconds]).pipe(
      map(([percent, totalTime]) => {
        if (percent === undefined) {
          return undefined;
        } else {
          return totalTime * percent / 100;
        }
      })
    );
    const nowTimeSeconds = dragTimeSeconds.pipe(
      switchMap(timeSeconds => timeSeconds === undefined ? this.audioPlayer.$globalProgressSeconds : of(timeSeconds))
    );

    this.$nowTime = nowTimeSeconds.pipe(
      map(progressSeconds => secondsToTimeFormat(progressSeconds))
    );
    this.$remainingTime = combineLatest([nowTimeSeconds, this.$totalNarratedSeconds])
      .pipe(map(([nowTime, totalTime]) => secondsToTimeFormat(nowTime - totalTime)));
    this.$nowPercent = combineLatest([nowTimeSeconds, this.$totalNarratedSeconds, this.$availablePercent])
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

    this.$playbackInfo
      .pipe(takeUntil(this.$destroy))
      .subscribe((playbackInfo) => {
        this.audioPlayer.initPlayer(this.bookWithContent().overview, playbackInfo);
      });
  }

  ngAfterViewInit() {
    this.sliderRect = this.slider.nativeElement.getBoundingClientRect();
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

  // --- Seek To / Drag ---
  /** Handle user clicking on a specific point in time on the progress bar. */
  onSliderClick(event: MouseEvent | TouchEvent) {
    const clientX = 'clientX' in event ? event.clientX : event.touches[0].clientX;
    const percent = this.getPercentFromEvent(clientX);
    this.seekToPercent(percent);
  }

  private isDragging = false;
  onDragStart(event: MouseEvent | TouchEvent) {
    event.preventDefault(); // Prevent default browser behavior like text selection
    this.isDragging = true;
  }

  @HostListener('document:mousemove', ['$event'])
  @HostListener('document:touchmove', ['$event'])
  onDrag(event: MouseEvent | TouchEvent) {
    if (!this.isDragging) {
      return;
    }

    const clientX = 'clientX' in event ? event.clientX : event.touches[0].clientX;
    const percent = this.getPercentFromEvent(clientX);

    this.$dragToPercent.next(percent);
  }

  @HostListener('document:mouseup')
  @HostListener('document:touchend')
  onDragEnd() {
    if (!this.isDragging) {
      return;
    }

    this.isDragging = false;
    const newPercent = this.$dragToPercent.value;
    if (newPercent !== undefined) {
      this.seekToPercent(newPercent);
    }
    setTimeout(() => {
      this.$dragToPercent.next(undefined);
    }, 500);
  }

  private getPercentFromEvent(clientX: number): number {
    const newLeft = clientX - this.sliderRect.left;
    let percent = (newLeft / this.sliderRect.width) * 100;
    percent = Math.max(0, Math.min(100, percent)); // Clamp between 0 and 100
    return percent;
  }

  private seekToPercent(percent: number) {
    const seekTime = this.convertPercentToSeconds(percent);
    this.audioPlayer.seekTo(seekTime);
  }

  private convertPercentToSeconds(percent: number): number {
    return (percent / 100) * this.audioPlayer.getDurationSeconds();
  }
  // --- Seek To / Drag ---

  ngOnDestroy(): void {
    this.audioPlayer.onDestroy();
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
