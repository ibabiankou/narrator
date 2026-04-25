import {
  AfterViewInit,
  Component,
  computed,
  ElementRef,
  HostListener,
  inject,
  input,
  OnDestroy,
  output,
  ViewChild
} from '@angular/core';
import { BookWithContent, PlaybackInfo } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import {
  BehaviorSubject,
  catchError,
  combineLatest,
  combineLatestWith,
  debounceTime,
  EMPTY,
  filter,
  interval,
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
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { BooksService } from '../../core/services/books.service';
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';
import { MatSlideToggle } from '@angular/material/slide-toggle';
import { SettingsService } from '../../core/services/settings.service';
import { secondsToTimeFormat } from '../../core/utils';
import { FilesService } from '../../core/services/files.service';

@Component({
  selector: 'app-player',
  imports: [
    MatIcon,
    MatIconButton,
    AsyncPipe,
    DecimalPipe,
    MatMenu,
    MatMenuItem,
    MatMenuTrigger,
    MatSlideToggle
  ],
  templateUrl: './player.component.html',
  styleUrl: './player.component.scss',
})
export class PlayerComponent implements OnDestroy, AfterViewInit {
  @ViewChild('slider', {static: true}) slider!: ElementRef<HTMLDivElement>;
  @ViewChild('playbackSettingsMenuTrigger') trigger!: MatMenuTrigger;

  private $destroy = new Subject<boolean>();

  private bookService = inject(BooksService);
  private settingsService = inject(SettingsService);
  private filesService = inject(FilesService);
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

  private preferences = toSignal(this.settingsService.userPreferences$);

  sectionPlayed = output<number>();
  syncCurrentSection = computed(() => !!this.preferences()!["auto_scroll"]);

  fontSizePx = computed(() => <number>this.preferences()!["text_size"]);

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
    this.audioPlayer = new AudioPlayer(this.bookService, this.filesService);

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

    //--- User preferences ---
    this.settingsService.userPreferences$
      .pipe(take(1))
      .subscribe(preferences => {
        // Passing through initial configurations;
        this.setFontSizeStyle(preferences["text_size"]);
        this.audioPlayer.setPlaybackRate(preferences["playback_rate"]);
      });
    this.audioPlayer.$playbackRate.pipe(
      debounceTime(1000),
      switchMap(newRate => {
        if (newRate != this.preferences()!["playback_rate"]) {
          return this.settingsService.patch("user_preferences", {"playback_rate": newRate});
        }
        return EMPTY
      }),
      takeUntil(this.$destroy)
    ).subscribe();

    interval(5000)
      .pipe(
        takeUntil(this.$destroy),
        combineLatestWith(this.$isPlaying)
      ).subscribe(async ([_, isPlaying]) => {
      if (isPlaying) {
        await this.requestWakeLock();
      } else {
        this.releaseWakeLock();
      }
    });
  }

  ngAfterViewInit() {
    this.sliderRect = this.slider.nativeElement.getBoundingClientRect();
  }

  @HostListener('document:keyup.s')
  handleKeyboardEvent() {
    if (this.trigger.menuOpen) {
      this.trigger.closeMenu();
    } else {
      this.trigger.openMenu();
    }
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
  increasePlaybackRate(e: Event, adjustment: number = 0.05) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.adjustPlaybackRate(adjustment);
  }

  @HostListener("document:keydown.shift.arrowdown", ["$event"])
  lowerPlaybackRate(e: Event, adjustment: number = -0.05) {
    if (!this.handleKeyBindings()) {
      return;
    }
    e.preventDefault();
    this.adjustPlaybackRate(adjustment);
  }

  adjustPlaybackRate(adjustment: number) {
    this.audioPlayer.adjustPlaybackRate(adjustment);
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

  // --- Wake Lock ---

  private wakeLock: any = null;

  async requestWakeLock() {
    try {
      if ('wakeLock' in navigator && this.wakeLock == null) {
        this.wakeLock = await (navigator as any).wakeLock.request('screen');
        this.wakeLock.addEventListener('release', () => {
          this.wakeLock = null;
        });
      }
    } catch (err: any) {
      console.error(`${err.name}, ${err.message}`);
    }
  }

  releaseWakeLock() {
    if (this.wakeLock !== null) {
      this.wakeLock.release().then(() => {
        this.wakeLock = null;
      });
    }
  }

  // Keep the screen awake while playing audio.
  @HostListener('document:visibilitychange')
  async handleVisibilityChange() {
    if (document.visibilityState !== 'visible') {
      this.releaseWakeLock();
    } else {
      await this.requestWakeLock();
    }
  }

  // --- Wake Lock; end ---

  ngOnDestroy(): void {
    this.audioPlayer.onDestroy();
    this.releaseWakeLock();
    this.$destroy.next(true);
    this.$destroy.complete();
  }

  toggleSync() {
    const newValue = !this.syncCurrentSection();
    if (!newValue) {
      this.sectionPlayed.emit(0);
    } else {
      this.audioPlayer.$sectionId.pipe(take(1))
        .subscribe(sectionId => this.sectionPlayed.emit(sectionId));
    }
    this.settingsService.patchUserPreferences({auto_scroll: newValue});
  }

  protected setFontSizePx(px: number) {
    this.setFontSizeStyle(px);
    this.settingsService.patchUserPreferences({text_size: px});
  }

  private setFontSizeStyle(px: number) {
    const element = document.querySelector('app-view-book-page') as HTMLElement;
    if (element) {
      element.style.setProperty('--book-font-size', `${px}px`);
    } else {
      console.warn("Could not find app-view-book-page element");
    }
  }
}
