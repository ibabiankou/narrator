import { BookDetails, PlaybackProgress } from '../../core/models/books.dto';
import { environment } from '../../../environments/environment';
import {
  BehaviorSubject,
  combineLatest, combineLatestWith,
  distinctUntilChanged,
  filter, interval,
  map, switchMap, take, tap,
} from 'rxjs';
import { Injectable } from '@angular/core';
import { PlaylistsService } from '../../core/services/playlists.service';

import Hls from 'hls.js';

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
@Injectable({providedIn: 'root'})
export class AudioPlayerService {
  private $status = new BehaviorSubject<PlayerStatus>(PlayerStatus.paused);
  private readonly audio: HTMLAudioElement;
  private hls: Hls | null = null;

  $bookDetails = new BehaviorSubject<BookDetails | null>(null);
  // A list of sections from the HLS playlist along with their duration and end time.
  private sectionTimeline: HlsSection[] = [];
  // Currently playing time in seconds.
  $globalProgressSeconds = new BehaviorSubject<number>(0);
  // An index within sectionTimeline of the currently playing section.
  private $sectionIndex = this.$globalProgressSeconds.pipe(
    map(currentTime => binarySearch(this.sectionTimeline, (section) => section.end_time, currentTime) - 1),
    filter(index => index >= 0),
    map(i => i + 1),
    distinctUntilChanged(),
    tap(i => console.log(`Current section index:`, i)),
  );
  // An ID of the section that is being played right now.
  $sectionId = this.$sectionIndex.pipe(
    map(i => this.sectionTimeline[i].section_id),
    tap(i => console.log(`Current section id:`, i)),
  );

  $playbackRate = new BehaviorSubject<number>(1);
  $isPlaying = this.$status.pipe(map((status) => status == PlayerStatus.playing));

  constructor(private playlistService: PlaylistsService) {
    this.audio = new Audio();
    this.audio.preservesPitch = true;
    this.audio.addEventListener('timeupdate', () => this.readProgress());

    this.$bookDetails
      .pipe(filter(book => book != null))
      .subscribe((book) => {

        if (Hls.isSupported()) {
          this.hls = new Hls({
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
              console.log(hlsSections);
            } else {
              console.warn("No date ranges found, unable to sync section being played.")
            }
          });

          this.hls.loadSource(`${environment.api_base_url}/books/${book.id}/m3u8`);
          this.hls.attachMedia(this.audio);
        } else {
          console.error("HLS not supported");
        }
      });

    this.$playbackRate.subscribe(() => {
      if (this.audio) {
        this.audio.playbackRate = this.$playbackRate.value;
      }
    });

    interval(5000)
      .pipe(
        combineLatestWith(this.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
      ).subscribe(() => this.updateProgress());
  }

  private readProgress() {
    this.$globalProgressSeconds.next(this.audio.currentTime);
  }

  private updateProgress() {
    combineLatest([this.$bookDetails.pipe(filter(b => b != null)), this.$globalProgressSeconds, this.$playbackRate])
      .pipe(
        take(1),
        switchMap(([bookDetails, progressSeconds, playbackRate]) => {
          return this.playlistService.updateProgress({
            "book_id": bookDetails.id,
            "data": {
              "progress_seconds": progressSeconds,
              "sync_current_section": true,
              "playback_rate": playbackRate
            }
          });
        })
      ).subscribe();
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
      this.$status.next(PlayerStatus.paused);
    }
  }

  next() {
    this.$sectionIndex.pipe(take(1))
      .subscribe(i => {
        // Scrolling to the end time of the current section, effectively starting the next one.
        this.audio.currentTime = this.sectionTimeline[i].end_time
      });
  }

  previous() {
    this.$sectionIndex.pipe(take(1))
      .subscribe(i => {
        // The end time of the previous section is the start time of the current section, so
        // to play the previous section, we need to go two items back.
        // Add a few extra ms, otherwise it activates the one before previous section for a moment.
        this.audio.currentTime = this.sectionTimeline[Math.max(i - 2, 0)].end_time + 0.05;
      });
  }

  seek(adjustment: number) {
    this.audio.currentTime += adjustment;
  }

  seekTo(seekTime: number | undefined) {
    if (seekTime == undefined) {
      return;
    }
    this.audio.currentTime = seekTime;
  }

  adjustPlaybackRate(adjustment: number) {
    const maxValue = 2;
    const minValue = 0.5;
    const newRate = this.$playbackRate.value + adjustment;
    this.$playbackRate.next(Math.max(Math.min(newRate, maxValue), minValue));
  }

  setBookDetails(book: BookDetails) {
    this.$bookDetails.next(book);
  }

  setPlaybackProgress(progress: PlaybackProgress) {
    this.$playbackRate.next(progress.playback_rate);
    this.audio.currentTime = progress.global_progress_seconds
  }
}

// Returns index of the element with the largest value smaller than target.
function binarySearch<T>(arr: T[], keyExtractor: (item: T) => number, target: number): number {
  let left = 0;
  let right = arr.length;

  while (left < right) {
    const mid = Math.floor(left + (right - left) / 2);

    if (keyExtractor(arr[mid]) <= target) {
      left = mid + 1;
    } else {
      right = mid;
    }
  }

  return left < arr.length ? left : -1;
}
