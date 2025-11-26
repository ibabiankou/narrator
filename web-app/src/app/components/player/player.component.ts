import { Component, input, OnDestroy, OnInit, signal } from '@angular/core';
import { AudioTrack, Playlist } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { environment } from '../../../environments/environment';
import { BooksService } from '../../core/services/books.service';
import {
  BehaviorSubject, combineLatest,
  filter,
  interval,
  map,
  Subject,
  Subscription,
  takeUntil,
  zip,
} from 'rxjs';
import { AsyncPipe } from '@angular/common';

declare const Amplitude: any;

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

  isPlaying = signal<boolean>(false);

  playerState: PlayerState | null = null;

  constructor(private bookService: BooksService) {
  }

  ngOnDestroy(): void {
    this.playerState?.destroy();
  }

  ngOnInit(): void {
    this.playerState = new PlayerState(this.bookService, this.playlist());
  }

  nowPercent() {
    const progress = this.playlist().progress
    return progress.available_percent * progress.global_progress_seconds / progress.total_narrated_seconds;
  }

  // TODO: Auto-scroll to the currently played item. I should probably simply emmit event what is being played
  //  (upon start and periodically)
  //  and let the page do the scrolling.

  playPause() {
    if (this.isPlaying()) {
      Amplitude.pause();
    } else {
      Amplitude.play();
    }
    this.isPlaying.update(value => !value);
  }
}

// A single place for all logic around managing the state of the player.
class PlayerState {
  $destroy = new Subject<boolean>();
  readerSubscription: Subscription;

  tracks: AudioTrack[];
  // Holds global book time at which each track starts.
  durationSum: number[] = [0];

  private readonly $currentTrackIndex;
  private readonly $currentTrackProgressSeconds;

  // Progress from the start of the book.
  private readonly $progressSeconds;
  // Total duration of the narrated part.
  private readonly $totalNarratedSeconds;

  $nowTime;
  $remainingTime;

  constructor(private bookService: BooksService, playlist: Playlist) {
    // Read initial values from the playlist.
    this.tracks = playlist.tracks;
    this.durationSum.push(this.tracks[0].duration);
    for (let i = 0; i < this.tracks.length; i++) {
      this.durationSum.push(this.durationSum[i] + this.tracks[i].duration);
    }

    let trackIndex = 0;
    if (playlist.progress.section_id) {
      trackIndex = this.tracks.findIndex(t => t.section_id == playlist.progress.section_id);
    }
    this.$currentTrackIndex = new BehaviorSubject<number>(trackIndex);

    const trackProgressSeconds = playlist.progress.section_progress_seconds || 0;
    this.$currentTrackProgressSeconds = new BehaviorSubject<number>(trackProgressSeconds);

    this.$totalNarratedSeconds = new BehaviorSubject<number>(playlist.progress.total_narrated_seconds);
    this.$progressSeconds = zip(this.$currentTrackIndex, this.$currentTrackProgressSeconds)
      .pipe(map(([index, progress]) => this.durationSum[index] + progress));
    this.$nowTime = this.$progressSeconds.pipe(
      map(progressSeconds => secondsToTimeFormat(progressSeconds))
    );
    this.$remainingTime = combineLatest([this.$progressSeconds, this.$totalNarratedSeconds])
      .pipe(map(([nowTime, totalTime]) => secondsToTimeFormat(nowTime - totalTime)));


    const baseUrl = environment.api_base_url
    for (let i = 0; i < this.tracks.length; i++) {
      let track = this.tracks[i];
      track.url = `${baseUrl}/books/${track.book_id}/speech/${track.file_name}`
    }
    Amplitude.init({
      songs: this.tracks,
      start_song: trackIndex,
      playback_speed: 1,
      debug: !environment.production
    });
    if (this.tracks) {
      Amplitude.setSongPlayedPercentage(trackProgressSeconds / this.tracks[trackIndex].duration * 100);
    }


    this.readerSubscription = interval(1000)
      .pipe(
        filter(() => Amplitude.getPlayerState() == "playing"),
        takeUntil(this.$destroy),
      ).subscribe(() => this.readProgress());

    // TODO: Start a "timer" to save progress every 5 seconds of playback.
  }

  readProgress() {
    const track = Amplitude.getActiveSongMetadata();
    this.$currentTrackIndex.next(track.index);
    this.$currentTrackProgressSeconds.next(Amplitude.getSongPlayedSeconds());
  }

  destroy() {
    Amplitude.pause();
    this.$destroy.next(true);
    this.$destroy.complete();
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
