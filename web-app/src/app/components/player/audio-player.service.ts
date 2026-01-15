import { AudioTrack, BookDetails, PlaybackProgress } from '../../core/models/books.dto';
import { environment } from '../../../environments/environment';
import {
  BehaviorSubject,
  combineLatest,
  distinct,
  filter,
  map,
} from 'rxjs';
import { Injectable } from '@angular/core';
import { PlaylistsService } from '../../core/services/playlists.service';

import Hls from 'hls.js';

interface PlayerTrack {
  audioTrack: AudioTrack

  url: string;
  index: number;
}

enum PlayerStatus {
  playing = "playing",
  paused = "paused",
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
  private tracks: PlayerTrack[] = [];
  // Holds global book time at which each track starts.
  private durationSum: number[] = [0];

  private $trackIndex = new BehaviorSubject<number>(0);
  $playbackRate = new BehaviorSubject<number>(1);

  $isPlaying = this.$status.pipe(map((status) => status == PlayerStatus.playing));

  $audioTrack = combineLatest([this.$trackIndex.pipe(distinct()), this.$isPlaying])
    .pipe(
      filter(([_, isPlaying]) => isPlaying),
      map(([trackIndex, _]) => this.tracks[trackIndex]?.audioTrack),
      filter(track => track != null),
      distinct()
    );

  // Progress from the start of the book.
  $globalProgressSeconds = new BehaviorSubject<number>(0);

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
          this.hls.loadSource(`${environment.api_base_url}/books/${book.id}/stream.m3u8`);
          this.hls.attachMedia(this.audio);
        } else {
          console.error("HLS not supported");
        }
      });

    this.$globalProgressSeconds
      .subscribe((currentTime) => {
        const trackIndex = binarySearch(this.durationSum, currentTime) - 1;
        if (trackIndex >= 0) {
          this.$trackIndex.next(trackIndex);
        }
      });

    this.$playbackRate.subscribe(() => {
      if (this.audio) {
        this.audio.playbackRate = this.$playbackRate.value;
      }
    });
  }

  private readProgress() {
    this.$globalProgressSeconds.next(this.audio.currentTime);
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
    this.audio.currentTime = this.durationSum[this.$trackIndex.value + 1];
  }

  previous() {
    this.audio.currentTime = this.durationSum[this.$trackIndex.value - 1];
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

function binarySearch(arr: number[], target: number): number {
  let left = 0;
  let right = arr.length; // Use length to allow for "not found" (index out of bounds)

  while (left < right) {
    const mid = Math.floor(left + (right - left) / 2);

    if (arr[mid] <= target) {
      // If the middle element is less than or equal to target,
      // the first "larger" element must be to the right.
      left = mid + 1;
    } else {
      // If the middle element is already larger, it COULD be the first one,
      // but there might be an even earlier one to the left.
      right = mid;
    }
  }

  // After the loop, left == right, pointing to the first element > target
  return left < arr.length ? left : -1;
}
