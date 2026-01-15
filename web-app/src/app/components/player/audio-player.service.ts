import { AudioTrack, BookDetails, PlaybackProgress } from '../../core/models/books.dto';
import { environment } from '../../../environments/environment';
import {
  BehaviorSubject,
  combineLatest,
  distinct,
  filter,
  map,
  take,
} from 'rxjs';
import { Injectable } from '@angular/core';
import { PlaylistsService } from '../../core/services/playlists.service';

interface PlayerTrack {
  audioTrack: AudioTrack

  url: string;
  index: number;
}

enum PlayerStatus {
  stopped = "stopped",
  playing = "playing",
  paused = "paused",
}

/**
 * Responsible for playback logic: Playing each track, navigating back and forth, changing tracks.
 */
@Injectable({providedIn: 'root'})
export class AudioPlayerService {
  private $status = new BehaviorSubject<PlayerStatus>(PlayerStatus.stopped);
  private readonly audio: HTMLAudioElement;

  $bookDetails = new BehaviorSubject<BookDetails | null>(null);
  private tracks: PlayerTrack[] = [];
  // Holds global book time at which each track starts.
  private durationSum: number[] = [0];

  private $currentTime = new BehaviorSubject<number>(0);

  $trackIndex = new BehaviorSubject<number>(0);
  private $trackOffset = new BehaviorSubject<number>(0);
  private $currentContextTime = new BehaviorSubject<number>(0);
  $playbackRate = new BehaviorSubject<number>(1);

  $isPlaying = this.$status.pipe(map((status) => status == PlayerStatus.playing));

  $audioTrack = combineLatest([this.$trackIndex, this.$isPlaying])
    .pipe(
      filter(([_, isPlaying]) => isPlaying),
      map(([trackIndex, _]) => this.tracks[trackIndex]?.audioTrack),
      filter(track => track != null),
      distinct()
    );

  // Progress from the start of the book.
  $globalProgressSeconds = this.$currentContextTime;

  constructor(private playlistService: PlaylistsService) {
    this.audio = new Audio();
    this.audio.preservesPitch = true;
    this.audio.addEventListener('timeupdate', () => this.readProgress());

    this.$playbackRate.subscribe(() => {
      if (this.audio) {
        this.audio.playbackRate = this.$playbackRate.value;
      }
    });
  }

  private readProgress() {
    this.$currentContextTime.next(this.audio.currentTime);
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

  playTrack(trackIndex: number, offsetSeconds: number) {
    // TODO: Instead of setting track and offset, I should simply set the global progress,
    //  which will be translated into track and offset.
    // this.$trackIndex.next(trackIndex);
    // this.$trackOffset.next(offsetSeconds);
    // this.$currentContextTime.next(offsetSeconds);
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
    this.$trackIndex.pipe(take(1)).subscribe(
      (current) => {
        const next = current + 1;
        if (next >= this.tracks.length) {
          return;
        }
        this.playTrack(next, 0);
      });
  }

  previous() {
    this.$trackIndex.pipe(take(1)).subscribe(
      (current) => {
        const prev = current - 1;
        if (prev < 0) {
          return;
        }
        this.playTrack(prev, 0);
      });
  }

  getTrack(trackIndex: number) {
    return this.tracks[trackIndex].audioTrack;
  }

  seek(adjustment: number) {
    this.readProgress();
    combineLatest([this.$trackIndex, this.$currentContextTime]).pipe(take(1)).subscribe(
      ([trackIndex, trackProgressSeconds]) => {
        let track = this.getTrack(trackIndex);
        let newProgress = trackProgressSeconds + adjustment;

        if (newProgress < 0) {
          if (trackIndex == 0) {
            // Start from the beginning if it's the first track.
            this.playTrack(0, 0);
            return;
          } else {
            // It's not the first track, so go to the previous track.
            track = this.getTrack(trackIndex - 1);
            newProgress += track.duration;
            this.playTrack(trackIndex - 1, newProgress);
            return;
          }
        } else if (newProgress > track.duration) {
          if (trackIndex == this.tracks.length - 1) {
            // It's the last track, so seek the end. It should stop playback.
            this.playTrack(trackIndex, track.duration);
            return;
          } else {
            // Go to the next track.
            newProgress -= track.duration;
            this.playTrack(trackIndex + 1, newProgress);
            return;
          }
        } else {
          // We are within the current track, so simply change the progress.
          this.playTrack(trackIndex, newProgress);
          return;
        }
      });
  }

  seekTo(seekTime: number | undefined) {
    if (seekTime == undefined) {
      return;
    }

    for (let i = 0; i < this.durationSum.length; i++) {
      if (this.durationSum[i] > seekTime) {
        const trackIndex = i - 1;
        const trackOffset = seekTime - this.durationSum[trackIndex];
        this.playTrack(trackIndex, trackOffset);
        return;
      }
    }
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
    // TODO: Set global progress, seconds. Set total narrated duration.
    this.$playbackRate.next(progress.playback_rate);
    this.$currentTime.next(progress.global_progress_seconds);
  }
}
